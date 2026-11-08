import { env, exports } from "cloudflare:workers";
import { applyD1Migrations } from "cloudflare:test";
import { beforeAll, beforeEach, describe, expect, inject, it } from "vitest";

const appOrigin = "https://sophie-ultron-free-test.gandratecnologia.workers.dev";
let token = "";
let userId = "";
let username = "";
const migrations = inject("d1Migrations");

async function request(path: string, init: RequestInit = {}) {
  return env.DB ? exports.default.fetch(
    new Request(`https://worker.test${path}`, {
      ...init,
      headers: { Origin: appOrigin, ...(init.headers ?? {}) },
    }),
  ) : Promise.reject(new Error("D1 binding not available"));
}

beforeAll(async () => {
  await applyD1Migrations(env.DB, migrations);
});

beforeEach(async () => {
  await env.DB.exec("DELETE FROM ws_tickets; DELETE FROM tool_idempotency; DELETE FROM execution_plans; DELETE FROM automation_rules; DELETE FROM learning_experiences; DELETE FROM knowledge_fts; DELETE FROM knowledge_documents; DELETE FROM messages; DELETE FROM conversations; DELETE FROM sessions; DELETE FROM memories_fts; DELETE FROM memories; DELETE FROM settings; DELETE FROM memory_policies; DELETE FROM bootstrap_claim; DELETE FROM users;");
  username = `wanderson-${crypto.randomUUID().slice(0, 8)}`;
  const response = await request("/security/register", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Ultron-Bootstrap-Secret": "test-bootstrap-secret" },
    body: JSON.stringify({
      username,
      password: "ultron-test-password-2026",
      display_name: "Wanderson",
    }),
  });
  expect(response.status).toBe(201);
  const registration = await response.json() as { user_id: string };
  userId = registration.user_id;
  const login = await request("/security/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password: "ultron-test-password-2026" }),
  });
  expect(login.status).toBe(200);
  const payload = await login.json() as { user_id: string; access_token: string };
  userId = payload.user_id;
  token = payload.access_token;
});

describe("Cloudflare API authentication and persistence", () => {
  it("stores only a hash of the issued session token", async () => {
    const row = await env.DB.prepare("SELECT token_hash FROM sessions WHERE user_id = ?").bind(userId).first<{ token_hash: string }>();
    expect(row?.token_hash).toBeTruthy();
    expect(row?.token_hash).not.toBe(token);
  });

  it("authenticates through the private BFF bearer header", async () => {
    const response = await request("/security/status", { headers: { Authorization: `Bearer ${token}` } });
    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({ authenticated: true, user_id: userId, username });
  });

  it("keeps registration closed after the first account", async () => {
    const response = await request("/security/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "another-user", password: "another-long-test-password" }),
    });
    expect(response.status).toBe(403);
  });

  it("does not allow a user to read an unowned conversation", async () => {
    const response = await request(`/conversation/sessions/${crypto.randomUUID()}/messages`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(response.status).toBe(404);
  });

  it("rejects a cross-origin mutation before writing data", async () => {
    const before = await env.DB.prepare("SELECT COUNT(*) AS count FROM users").first<{ count: number }>();
    const response = await exports.default.fetch(new Request("https://worker.test/conversation/sessions", {
      method: "POST",
      headers: { Origin: "https://attacker.example", "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: "{}",
    }));
    expect(response.status).toBe(403);
    expect(await env.DB.prepare("SELECT COUNT(*) AS count FROM conversations").first<{ count: number }>()).toMatchObject({ count: 0 });
    expect(before?.count).toBe(1);
  });

  it("creates a conversation and persists its history under the owner", async () => {
    const response = await request("/conversation/sessions", { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: "{}" });
    expect(response.status).toBe(201);
    const session = await response.json() as { session_id: string; user_id: string };
    expect(session.user_id).toBe(userId);
    const count = await env.DB.prepare("SELECT COUNT(*) AS count FROM conversations WHERE user_id=?").bind(userId).first<{ count: number }>();
    expect(count?.count).toBe(1);
  });

  it("indexes, searches, and deletes only the owner's knowledge documents", async () => {
    const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
    const created = await request("/knowledge/documents", { method:"POST", headers, body:JSON.stringify({title:"Projeto Ultron",content:"Cloudflare D1 armazena documentos privados do agente.",source_type:"manual"}) });
    expect(created.status).toBe(201);
    const document = await created.json() as {id:string};
    const search = await request("/knowledge/search?q=Cloudflare%20D1", {headers:{Authorization:`Bearer ${token}`} });
    expect(search.status).toBe(200);
    expect(await search.json()).toMatchObject({hits:[{document_id:document.id,title:"Projeto Ultron"}]});
    const removed = await request(`/knowledge/documents/${document.id}`, {method:"DELETE",headers:{Authorization:`Bearer ${token}`} });
    expect(removed.status).toBe(200);
  });

  it("persists automation rules only for safe, confirmation-free tools", async () => {
    const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
    const invalid = await request("/automation/rules", {method:"POST",headers,body:JSON.stringify({name:"Salvar memória",event_type:"conversation.message.created",action_tool:"memory.remember",action_args:{content:"x"}})});
    expect(invalid.status).toBe(422);
    const created = await request("/automation/rules", {method:"POST",headers,body:JSON.stringify({name:"Consultar conhecimento",event_type:"conversation.message.created",action_tool:"knowledge.search",action_args:{query:"Ultron"}})});
    expect(created.status).toBe(201);
    const list = await request("/automation/rules", {headers:{Authorization:`Bearer ${token}`} });
    expect(await list.json()).toMatchObject({rules:[{name:"Consultar conhecimento",enabled:true,action_args:{query:"Ultron"}}]});
  });

  it("requires explicit confirmation before a plan stores a memory", async () => {
    const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
    const created = await request("/planner/plans", {method:"POST",headers,body:JSON.stringify({text:"Lembre que gosto de Cloudflare"})});
    expect(created.status).toBe(201);
    const plan = await created.json() as {plan_id:string;steps:Array<{step_id:string;requires_confirmation:boolean}>};
    expect(plan.steps[0]?.requires_confirmation).toBe(true);
    const blocked = await request(`/planner/plans/${plan.plan_id}/execute`, {method:"POST",headers,body:JSON.stringify({confirmed_step_ids:[]})});
    expect(await blocked.json()).toMatchObject({status:"confirmation_required"});
    const executed = await request(`/planner/plans/${plan.plan_id}/execute`, {method:"POST",headers,body:JSON.stringify({confirmed_step_ids:[plan.steps[0].step_id]})});
    const result = await executed.json() as {status:string;steps:Array<{status:string;tool_name:string|null}>};
    expect(result.status).toBe("completed");
    expect(result.steps).toContainEqual(expect.objectContaining({status:"completed",tool_name:"memory.remember"}));
  });
});
