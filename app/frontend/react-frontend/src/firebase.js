import { initializeApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  RecaptchaVerifier,
  PhoneAuthProvider,
  signInWithPhoneNumber,
  linkWithCredential,
} from "firebase/auth";

// Firebase project config
const firebaseConfig = {
  apiKey: "AIzaSyCpHRWOXdN7YNmzdyJoBQaxPNXdfem9Wjg",
  authDomain: "home-loan-49875.firebaseapp.com",
  projectId: "home-loan-49875",
  storageBucket: "home-loan-49875.firebasestorage.app",
  messagingSenderId: "150763436734",
  appId: "1:150763436734:web:c1e21b7b43e65cf76b3cef",
  measurementId: "G-8RS6Q832Q0",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();

// Phone auth helpers
export { RecaptchaVerifier, PhoneAuthProvider, signInWithPhoneNumber, linkWithCredential };
