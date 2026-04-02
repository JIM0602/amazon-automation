/**
 * JWT token management via browser cookies.
 * Phase 3a: Uses non-httpOnly cookies for client-side access.
 * Phase 3b: Will harden with httpOnly server-side cookies.
 */

const TOKEN_COOKIE = "token";
const REFRESH_TOKEN_COOKIE = "refresh_token";

/**
 * Read the access token from document.cookie
 */
export function getToken(): string | null {
  if (typeof document === "undefined") return null;

  const cookies = document.cookie.split(";");
  for (const cookie of cookies) {
    const [name, ...rest] = cookie.trim().split("=");
    if (name === TOKEN_COOKIE) {
      return decodeURIComponent(rest.join("="));
    }
  }
  return null;
}

/**
 * Read the refresh token from document.cookie
 */
export function getRefreshToken(): string | null {
  if (typeof document === "undefined") return null;

  const cookies = document.cookie.split(";");
  for (const cookie of cookies) {
    const [name, ...rest] = cookie.trim().split("=");
    if (name === REFRESH_TOKEN_COOKIE) {
      return decodeURIComponent(rest.join("="));
    }
  }
  return null;
}

/**
 * Store access and refresh tokens in cookies.
 * SameSite=Strict for CSRF protection; Secure flag handled by browser on HTTPS.
 */
export function setToken(accessToken: string, refreshToken: string): void {
  if (typeof document === "undefined") return;

  // Set access token — expires in 30 minutes
  document.cookie = `${TOKEN_COOKIE}=${encodeURIComponent(accessToken)};path=/;max-age=1800;SameSite=Strict`;
  // Set refresh token — expires in 7 days
  document.cookie = `${REFRESH_TOKEN_COOKIE}=${encodeURIComponent(refreshToken)};path=/;max-age=604800;SameSite=Strict`;
}

/**
 * Remove both token cookies by setting max-age=0
 */
export function clearTokens(): void {
  if (typeof document === "undefined") return;

  document.cookie = `${TOKEN_COOKIE}=;path=/;max-age=0;SameSite=Strict`;
  document.cookie = `${REFRESH_TOKEN_COOKIE}=;path=/;max-age=0;SameSite=Strict`;
}

/**
 * Return Authorization header object if token exists, otherwise empty object.
 */
export function getAuthHeaders(): Record<string, string> {
  const token = getToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}
