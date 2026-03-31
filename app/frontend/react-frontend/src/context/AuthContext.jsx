import { createContext, useContext, useState, useEffect, useCallback } from "react";
import {
  onAuthStateChanged,
  signInWithPopup,
  signInWithRedirect,
  signOut as firebaseSignOut,
  setPersistence,
  browserSessionPersistence,
} from "firebase/auth";
import { auth, googleProvider } from "../firebase";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authActionLoading, setAuthActionLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const [backendPhoneLinked, setBackendPhoneLinked] = useState(false);

  // Derived: true when user has a phone number linked to their account OR mapped in backend
  const phoneLinked = Boolean(user?.phoneNumber) || backendPhoneLinked;

  useEffect(() => {
    // 1. Enforce session persistence (clears on tab close)
    setPersistence(auth, browserSessionPersistence).catch((error) => {
      console.error("Firebase persistence error:", error);
    });

    // 2. Auth state listener
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      if (firebaseUser?.email) {
        try {
          const res = await fetch(`http://localhost:8000/get-phone?email=${encodeURIComponent(firebaseUser.email)}`);
          if (res.ok) {
            const data = await res.json();
            setBackendPhoneLinked(data.status === "ok" && !!data.phone_number);
          } else {
            setBackendPhoneLinked(false);
          }
        } catch (err) {
          console.error("Failed to check backend phone status:", err);
          setBackendPhoneLinked(false);
        }
      } else {
        setBackendPhoneLinked(false);
      }
      setLoading(false);
    });

    // 3. Failsafe: forcibly sign out on page unload / refresh
    const handleBeforeUnload = () => {
      if (auth.currentUser) {
        firebaseSignOut(auth);
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      unsubscribe();
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, []);

  const signInWithGoogle = async () => {
    setAuthError("");
    setAuthActionLoading(true);
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (err) {
      if (err?.code === "auth/popup-blocked" || err?.code === "auth/popup-closed-by-user") {
        try {
          await signInWithRedirect(auth, googleProvider);
          return;
        } catch (redirectErr) {
          console.error("Google redirect sign-in failed:", redirectErr);
          setAuthError("Unable to complete Google sign-in. Please try again.");
          return;
        }
      }
      setAuthError("Google sign-in failed. Please try again.");
      console.error("Google sign-in failed:", err);
    } finally {
      setAuthActionLoading(false);
    }
  };

  const signOut = async () => {
    setAuthError("");
    setAuthActionLoading(true);
    try {
      await firebaseSignOut(auth);
    } catch (err) {
      setAuthError("Sign-out failed. Please try again.");
      console.error("Sign-out failed:", err);
    } finally {
      setAuthActionLoading(false);
    }
  };

  /**
   * Refresh the Firebase user object (e.g. after linking phone credential).
   * This forces onAuthStateChanged to re-fire with updated provider data.
   */
  const refreshUser = useCallback(async () => {
    if (auth.currentUser) {
      await auth.currentUser.reload();
      setUser({ ...auth.currentUser });
    }
  }, []);

  const clearAuthError = () => setAuthError("");

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        phoneLinked,
        authActionLoading,
        authError,
        signInWithGoogle,
        signOut,
        refreshUser,
        clearAuthError,
        setBackendPhoneLinked,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
