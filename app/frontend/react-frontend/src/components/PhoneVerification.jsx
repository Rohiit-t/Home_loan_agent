import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import {
  auth,
  RecaptchaVerifier,
  PhoneAuthProvider,
  signInWithPhoneNumber,
  linkWithCredential,
} from "../firebase";

const BACKEND_URL = "http://localhost:8000";

/**
 * PhoneVerification — Mandatory phone number linking after Google sign-in.
 *
 * Flow:
 *  1. User enters phone number
 *  2. Invisible reCAPTCHA verifies human
 *  3. Firebase sends OTP via SMS
 *  4. User enters OTP
 *  5. OTP verified → phone credential linked to existing Google user
 *  6. Verified phone number sent to backend /save-phone
 *  7. Redirect to landing page
 */
export default function PhoneVerification({ onVerified }) {
  const { user, refreshUser, signOut, setBackendPhoneLinked } = useAuth();

  // ── State ──────────────────────────────────────────────
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState("phone"); // "phone" | "otp" | "success"
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Refs for reCAPTCHA & confirmation result
  const recaptchaRef = useRef(null);
  const confirmationResultRef = useRef(null);
  const recaptchaContainerRef = useRef(null);

  // ── Cleanup reCAPTCHA on unmount ───────────────────────
  useEffect(() => {
    return () => {
      if (recaptchaRef.current) {
        try {
          recaptchaRef.current.clear();
        } catch {
          // Ignore cleanup errors for already disposed reCAPTCHA instances.
        }
        recaptchaRef.current = null;
      }
    };
  }, []);

  // ── Initialize invisible reCAPTCHA ─────────────────────
  const setupRecaptcha = useCallback(() => {
    if (recaptchaRef.current) return;

    recaptchaRef.current = new RecaptchaVerifier(auth, recaptchaContainerRef.current, {
      size: "invisible",
      callback: () => {
        // reCAPTCHA solved — will proceed automatically
      },
      "expired-callback": () => {
        setError("reCAPTCHA expired. Please try again.");
        recaptchaRef.current = null;
      },
    });
  }, []);

  // ── Friendly error messages ────────────────────────────
  const getFriendlyError = (code) => {
    const map = {
      "auth/invalid-phone-number": "Invalid phone number. Please include country code (e.g. +91...).",
      "auth/too-many-requests": "Too many attempts. Please wait a few minutes and try again.",
      "auth/code-expired": "OTP has expired. Please request a new one.",
      "auth/invalid-verification-code": "Invalid OTP. Please check and try again.",
      "auth/credential-already-in-use": "This phone number is already linked to another account.",
      "auth/provider-already-linked": "A phone number is already linked to this account.",
      "auth/account-exists-with-different-credential": "This phone number is linked to a different account. Please use another number or sign out.",
      "auth/captcha-check-failed": "reCAPTCHA verification failed. Please refresh and try again.",
      "auth/quota-exceeded": "SMS quota exceeded. Please try again later.",
      "auth/billing-not-enabled": "Firebase billing is disabled. Please use a configured TEST phone number.",
    };
    return map[code] || "Something went wrong. Please try again.";
  };

  // ── Step 1: Send OTP ───────────────────────────────────
  const handleSendOTP = async (e) => {
    e.preventDefault();
    setError("");
    setSuccessMsg("");

    const trimmed = phone.trim();
    if (!trimmed) {
      setError("Please enter your phone number.");
      return;
    }
    // Basic validation: must start with + and have at least 10 digits
    if (!/^\+\d{10,15}$/.test(trimmed)) {
      setError("Enter a valid phone number with country code (e.g. +919876543210).");
      return;
    }

    setLoading(true);
    try {
      setupRecaptcha();
      const confirmation = await signInWithPhoneNumber(auth, trimmed, recaptchaRef.current);
      confirmationResultRef.current = confirmation;
      setStep("otp");
      setSuccessMsg("OTP sent! Check your phone.");
    } catch (err) {
      console.error("Send OTP error:", err);
      setError(getFriendlyError(err.code));
      // Reset reCAPTCHA so it can be used again
      if (recaptchaRef.current) {
        try {
          recaptchaRef.current.clear();
        } catch {
          // Ignore cleanup errors while recreating reCAPTCHA.
        }
        recaptchaRef.current = null;
      }
    } finally {
      setLoading(false);
    }
  };

  // ── Step 2: Verify OTP & Link credential ───────────────
  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    setError("");
    setSuccessMsg("");

    const trimmedOtp = otp.trim();
    if (!trimmedOtp || trimmedOtp.length !== 6) {
      setError("Please enter the 6-digit OTP.");
      return;
    }

    setLoading(true);
    try {
      // Create phone credential from the verification ID + user-entered OTP
      const credential = PhoneAuthProvider.credential(
        confirmationResultRef.current.verificationId,
        trimmedOtp
      );

      // Try to link phone credential to the currently signed-in Google user
      let isDuplicateError = false;
      try {
        await linkWithCredential(user, credential);
      } catch (linkErr) {
        if (
          linkErr.code === "auth/account-exists-with-different-credential" ||
          linkErr.code === "auth/credential-already-in-use"
        ) {
          // The OTP was valid! We just couldn't link it to THIS Google account.
          // This is a successful verification for our multi-account logic.
          isDuplicateError = true;
        } else {
          // Re-throw other errors (invalid OTP, expired, etc.)
          throw linkErr;
        }
      }

      // Refresh user state
      await refreshUser();

      const updatedUser = auth.currentUser;
      // If duplicate, Firebase didn't link it, so use the user-entered phone number
      const verifiedPhone = isDuplicateError ? phone : updatedUser.phoneNumber;

      // Send verified phone to backend
      try {
        const res = await fetch(`${BACKEND_URL}/save-phone`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            uid: updatedUser.uid,
            email: updatedUser.email,
            phone_number: verifiedPhone,
          }),
        });
        if (!res.ok) {
          console.warn("Backend /save-phone returned non-OK:", res.status);
        }
      } catch (backendErr) {
        console.warn("Failed to save phone to backend:", backendErr);
      }

      // Tell AuthContext that the backend phone is linked
      setBackendPhoneLinked(true);

      setStep("success");
      setSuccessMsg("Phone number verified successfully!");

      // Auto-redirect after 2 seconds
      setTimeout(() => {
        onVerified();
      }, 2000);
    } catch (err) {
      console.error("Verify OTP error:", err);
      setError(getFriendlyError(err.code));
    } finally {
      setLoading(false);
    }
  };

  // ── Resend OTP ─────────────────────────────────────────
  const handleResendOTP = async () => {
    setOtp("");
    setStep("phone");
    setError("");
    setSuccessMsg("");
    // Reset reCAPTCHA
    if (recaptchaRef.current) {
      try {
        recaptchaRef.current.clear();
      } catch {
        // Ignore cleanup errors while resetting reCAPTCHA.
      }
      recaptchaRef.current = null;
    }
  };

  // ── Render ─────────────────────────────────────────────
  return (
    <div className="phone-verify-page">
      <div className="phone-verify-card">
        {/* Invisible reCAPTCHA container */}
        <div ref={recaptchaContainerRef} id="recaptcha-container"></div>

        <div className="phone-verify-logo">📱</div>
        <h1 className="phone-verify-title">Verify Your Phone</h1>
        <p className="phone-verify-subtitle">
          A verified phone number is required to proceed.
          <br />
          <span className="phone-verify-email">Signed in as {user?.email}</span>
        </p>

        {/* ── Error Message ─── */}
        {error && (
          <div className="phone-verify-error">
            <span className="phone-verify-error-icon">⚠️</span>
            {error}
          </div>
        )}

        {/* ── Success Message ─── */}
        {successMsg && !error && (
          <div className="phone-verify-success">
            <span className="phone-verify-success-icon">✅</span>
            {successMsg}
          </div>
        )}

        {/* ── Step: Phone Input ─── */}
        {step === "phone" && (
          <form className="phone-verify-form" onSubmit={handleSendOTP}>
            <label className="phone-verify-label" htmlFor="phone-input">
              Phone Number (with country code)
            </label>
            <input
              id="phone-input"
              className="phone-verify-input"
              type="tel"
              placeholder="+919876543210"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              disabled={loading}
              autoFocus
            />
            <button className="phone-verify-btn" type="submit" disabled={loading}>
              {loading ? (
                <span className="phone-verify-spinner"></span>
              ) : (
                "Send OTP"
              )}
            </button>
          </form>
        )}

        {/* ── Step: OTP Input ─── */}
        {step === "otp" && (
          <form className="phone-verify-form" onSubmit={handleVerifyOTP}>
            <label className="phone-verify-label" htmlFor="otp-input">
              Enter 6-digit OTP
            </label>
            <input
              id="otp-input"
              className="phone-verify-input otp-input"
              type="text"
              inputMode="numeric"
              maxLength={6}
              placeholder="123456"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
              disabled={loading}
              autoFocus
            />
            <button className="phone-verify-btn" type="submit" disabled={loading}>
              {loading ? (
                <span className="phone-verify-spinner"></span>
              ) : (
                "Verify & Link"
              )}
            </button>
            <button
              type="button"
              className="phone-verify-link-btn"
              onClick={handleResendOTP}
              disabled={loading}
            >
              ← Change number / Resend OTP
            </button>
          </form>
        )}

        {/* ── Step: Success ─── */}
        {step === "success" && (
          <div className="phone-verify-done">
            <div className="phone-verify-done-icon">🎉</div>
            <p>Redirecting you to the app...</p>
          </div>
        )}

        {/* Sign-out option */}
        <button className="phone-verify-signout" onClick={signOut} disabled={loading}>
          Sign out and use a different account
        </button>
      </div>
    </div>
  );
}
