"use client";
import { FormEvent, useState } from "react";
export default function AccountLogin({
  onToken,
}: {
  onToken: (token: string) => void;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const values = new FormData(form);
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: values.get("username"),
          password: values.get("password"),
        }),
      });
      const body = await response.json();
      if (!response.ok)
        throw new Error(
          typeof body.detail === "string"
            ? body.detail
            : "Sign-in fields are invalid",
        );
      form.reset();
      onToken(body.access_token);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <p>
        Use an account created by your workspace administrator. No public
        registration or default password is provided.
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <form onSubmit={login}>
        <label>
          Username
          <input
            name="username"
            minLength={3}
            maxLength={64}
            required
            autoComplete="username"
          />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            required
            maxLength={1024}
            autoComplete="current-password"
          />
        </label>
        <button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </>
  );
}
