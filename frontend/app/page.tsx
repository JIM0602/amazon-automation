import { redirect } from "next/navigation";

/**
 * Root page — redirect authenticated users to /dashboard.
 * The middleware handles unauthenticated users (redirects to /login).
 */
export default function RootPage() {
  redirect("/dashboard");
}
