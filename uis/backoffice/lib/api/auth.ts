import { authFetch } from "@healthcore/auth";

export const FORGOT_PASSWORD_CONFIRMATION =
  "If that address is registered, you'll receive a link shortly.";

export const RESET_PASSWORD_LOGIN_MESSAGE =
  "Password reset successfully. You can sign in with your new password.";

export async function forgotPassword(email: string): Promise<Response> {
  return fetch("/api/auth/forgot-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(token: string, newPassword: string): Promise<Response> {
  return fetch("/api/auth/reset-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export async function changePassword(
  currentPassword: string,
  newPassword: string
): Promise<Response> {
  return authFetch("/api/auth/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}
