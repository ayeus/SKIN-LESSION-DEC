"use client";
import { FormEvent, useEffect, useState } from "react";
type Data = Record<string, any>;
type Props = {
  api: (path: string, init?: RequestInit) => Promise<any>;
  datasets: { id: string; name: string; owner_id?: string | null }[];
};
export default function AccountPanel({ api, datasets }: Props) {
  const [me, setMe] = useState<Data | null>(null),
    [users, setUsers] = useState<Data[]>([]),
    [audits, setAudits] = useState<Data[] | null>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [dataset, setDataset] = useState(""),
    [grants, setGrants] = useState<Data[]>([]);
  async function load() {
    try {
      const identity = await api("/auth/me");
      setMe(identity);
      if (identity.role === "admin") setUsers(await api("/auth/users"));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await api("/auth/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      form.reset();
      setNotice(
        "Created " +
          result.username +
          ". Password is not stored in this browser.",
      );
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function inspect() {
    setError("");
    try {
      setGrants(await api("/datasets/" + dataset + "/grants"));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function grant(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setNotice("");
    const userId = String(new FormData(e.currentTarget).get("user_id"));
    try {
      await api("/datasets/" + dataset + "/grants", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      setNotice("Read access granted for the selected dataset.");
      await inspect();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <section className="panel">
      <h2>Accounts and data access</h2>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      {me?.id && (
        <p>
          User ID: <code>{me.id}</code>
        </p>
      )}
      {me && (
        <p>
          Signed in as <strong>{me.username}</strong> ({me.role}).{" "}
          {me.bootstrap
            ? "Environment owner token; rotate it to revoke its access."
            : "Session can be revoked by signing out or disabling the account."}
        </p>
      )}
      <p>
        Researchers see their own and explicitly granted datasets. Viewers
        cannot create analyses or upload data. Analysis reports are private to
        their creator and administrators.
      </p>
      {me?.role === "admin" && (
        <>
          <h3>Create a local account</h3>
          <form onSubmit={create}>
            <div className="form-grid">
              <label>
                New username
                <input
                  name="username"
                  minLength={3}
                  maxLength={64}
                  pattern="[A-Za-z0-9_.-]+"
                  required
                  autoComplete="off"
                />
              </label>
              <label>
                Initial password
                <input
                  name="password"
                  type="password"
                  minLength={12}
                  maxLength={1024}
                  required
                  autoComplete="new-password"
                />
              </label>
              <label>
                Role
                <select name="role">
                  <option value="researcher">Researcher</option>
                  <option value="viewer">Viewer</option>
                  <option value="admin">Administrator</option>
                </select>
              </label>
            </div>
            <button disabled={busy}>Create account</button>
          </form>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Role</th>
                  <th>User ID</th>
                  <th>Access</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.username}</td>
                    <td>{u.role}</td>
                    <td>{u.id}</td>
                    <td>
                      <button
                        disabled={u.id === me.id}
                        onClick={async () => {
                          setError("");
                          try {
                            await api("/auth/users/" + u.id, {
                              method: "PATCH",
                              headers: { "Content-Type": "application/json" },
                              body: JSON.stringify({ active: !u.active }),
                            });
                            await load();
                          } catch (e) {
                            setError((e as Error).message);
                          }
                        }}
                      >
                        {u.active
                          ? "Disable and revoke sessions"
                          : "Enable account"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {me && me.role !== "viewer" && datasets.length > 0 && (
        <>
          <h3>Dataset read grants</h3>
          <p>
            Only the dataset owner or an administrator can grant access.
            Granting a dataset does not share other users’ analysis reports.
            Revocation also blocks reports derived by the recipient from that
            dataset.
          </p>
          <label>
            Dataset
            <select
              value={dataset}
              onChange={(e) => {
                setDataset(e.target.value);
                setGrants([]);
              }}
            >
              <option value="">Select dataset you own or administer</option>
              {datasets
                .filter((d) => me?.role === "admin" || d.owner_id === me?.id)
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
            </select>
          </label>
          <button disabled={!dataset} onClick={() => void inspect()}>
            Inspect read grants
          </button>
          <form onSubmit={grant}>
            <label>
              Recipient user ID
              <input
                name="user_id"
                required
                placeholder="UUID from administrator or recipient's account profile"
              />
            </label>
            <button disabled={!dataset}>Grant dataset read access</button>
          </form>
          {grants.map((g) => (
            <p key={g.user_id}>
              {g.user_id}{" "}
              <button
                onClick={async () => {
                  try {
                    await api("/datasets/" + dataset + "/grants/" + g.user_id, {
                      method: "DELETE",
                    });
                    await inspect();
                    setNotice("Read grant revoked.");
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                Revoke read grant
              </button>
            </p>
          ))}
        </>
      )}
      {me?.role === "admin" && (
        <details>
          <summary>Research access audit</summary>
          <p>
            Actor IDs, actions, resources and timestamps only; no patient-note
            content or credentials.
          </p>
          <button
            onClick={async () => {
              try {
                setAudits(await api("/audit?limit=100"));
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            Load recent audit events
          </button>
          {audits && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Action</th>
                    <th>Actor</th>
                    <th>Resource</th>
                  </tr>
                </thead>
                <tbody>
                  {audits.map((a) => (
                    <tr key={a.id}>
                      <td>{new Date(a.created_at).toLocaleString()}</td>
                      <td>{a.action}</td>
                      <td>{a.actor_id || "Workspace owner / legacy"}</td>
                      <td>{a.resource_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </details>
      )}
      <p className="notice">
        Local identity controls are not clinical production approval. Shared
        hosting still requires TLS, institutional access policy, secure storage
        and operational review.
      </p>
    </section>
  );
}
