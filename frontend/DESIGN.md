# Medi-Mate Frontend — Architecture Design

> Companion to [`.claude/plans/PLAN.md`](../.claude/plans/PLAN.md). PLAN owns the **timeline** (what ships in week 1/2/3). DESIGN owns the **architecture** (how the frontend is structured and why).
> Author: drafted 2026-05-20 against backend commit `92c1c7c`. Scope: Week 2 MVP frontend.

---

## 0. Goals & Non-Goals

**Goals** — the architecture must:

1. Stream chat tokens from the existing WebSocket without losing frames on reconnect.
2. Hydrate historical messages (including `sources` and `emergency_level`) from REST on session load with the same render path as live messages.
3. Short-circuit to an emergency banner the instant the server signals it — no LLM-token rendering during emergencies.
4. Survive a 60-min access-token expiry without forcing the user to log in again (use the backend's existing refresh cookie).
5. Be deletable: every file under `frontend/` should be removable as one unit without touching backend code.

**Non-goals** — explicitly out of scope:

- SSR, RSC, framework-mode React Router. This is a static SPA served by nginx.
- Code splitting beyond what Vite does by default. Bundle size is not a Week 2 metric.
- A design-system package. Components live in `frontend/src/components/`, not a workspace.
- State sync across tabs. One tab, one session.
- i18n. Korean-only. UI copy can live inline.
- Offline mode / PWA. (See PLAN §2 — explicitly deferred.)

---

## 1. Stack & Versions

| Layer | Choice | Pinned because |
|---|---|---|
| Build tool | **Vite 6** (`@vitejs/plugin-react`) | Fast HMR; native ESM; first-class Tailwind v4 plugin |
| UI runtime | **React 19** | `useOptimistic` for chat input, `use()` for promise unwrap, stable Actions |
| Language | **TypeScript 5.6+** | Latest stable; `verbatimModuleSyntax` |
| Styles | **Tailwind CSS v4** via `@tailwindcss/vite` | CSS-first `@theme` — no `tailwind.config.ts`, no PostCSS plugin chain |
| Components | **shadcn/ui (v4 build)** via `npx shadcn@latest` | Copy-into-repo primitives; we own the source |
| Icons | **lucide-react** | Tree-shakable; consistent with shadcn |
| Server state | **TanStack Query v5** | Sessions list, message history, refetch policy |
| Client state | **Zustand 5** | Auth tokens, live chat stream buffer, UI flags |
| Routing | **React Router v7** (declarative SPA mode, **not** framework mode) | Familiar; no SSR coupling |
| HTTP | **fetch + thin wrapper** (`frontend/src/lib/api.ts`) | One file; no axios dependency for what amounts to an interceptor |
| Markdown | **react-markdown + remark-gfm + rehype-sanitize** | Render assistant output safely |
| Forms / validation | **react-hook-form + zod** (only if a form needs it) | Login is one button — likely no form library at all in week 2 |
| Tests | **Vitest 2 + @testing-library/react** | Vite-native; same config as build |
| Lint / format | **Biome 2** (single binary, replaces ESLint + Prettier) | Faster CI; if team prefers ESLint v9 + Prettier, that's also fine — pick one |
| Package manager | **pnpm** | Matches backend tooling preference (uv for python, pnpm for JS) |

**Node version**: pinned via `frontend/.nvmrc` to the active LTS at the time of scaffold (Node 22 LTS as of 2025). CI uses the same version.

**What we do NOT install**: axios, redux, MUI, styled-components, day.js (we use `Intl.DateTimeFormat`), socket.io-client (we use native `WebSocket`).

---

## 2. Folder Layout

```
frontend/
├── DESIGN.md                  # this file
├── README.md                  # short setup / run commands
├── package.json
├── pnpm-lock.yaml
├── tsconfig.json
├── vite.config.ts
├── Dockerfile                 # multi-stage: pnpm build → nginx:alpine
├── nginx.conf                 # SPA fallback + static cache headers
├── .env.example
├── .nvmrc
├── biome.json                 # or .eslintrc + .prettierrc if not using Biome
├── index.html
├── public/
│   ├── robots.txt
│   └── fonts/                 # self-hosted Pretendard Variable
└── src/
    ├── main.tsx               # Root mount: QueryClient + Router + ErrorBoundary
    ├── App.tsx                # Route shell
    ├── routes.tsx             # Route table (declarative)
    │
    ├── lib/                   # Cross-cutting infra (NOT React components)
    │   ├── env.ts             # Typed import.meta.env shim
    │   ├── api.ts             # fetch wrapper with auth header + 401 refresh
    │   ├── ws.ts              # WebSocket envelope types + connect helper
    │   ├── constants.ts       # DISCLAIMER text, emergency phone numbers
    │   └── markdown.ts        # Pre-configured react-markdown pipeline
    │
    ├── api/                   # Per-domain REST callers (use lib/api.ts)
    │   ├── auth.ts            # GET /auth/kakao/login, POST /auth/kakao/callback, GET /auth/token/refresh
    │   ├── chat.ts            # /chat/sessions, /chat/sessions/{id}/messages
    │   └── user.ts            # GET /users/me, DELETE /users/me
    │
    ├── store/                 # Zustand stores (client-only state)
    │   ├── authStore.ts       # access_token, user, hasSeenDisclaimer
    │   └── chatStore.ts       # current sessionId, in-flight stream buffer, emergency state
    │
    ├── hooks/                 # React hooks that bind store + side effects
    │   ├── useAuth.ts         # login/logout flow, refresh-on-401 trigger
    │   └── useChatSocket.ts   # WS connect/reconnect, envelope dispatch
    │
    ├── pages/                 # One file per route
    │   ├── Login.tsx
    │   ├── KakaoCallback.tsx
    │   └── Chat.tsx
    │
    ├── components/
    │   ├── chat/
    │   │   ├── MessageBubble.tsx
    │   │   ├── InputComposer.tsx     # Enter-to-send + IME composition guard
    │   │   ├── SessionSidebar.tsx
    │   │   ├── CitationCard.tsx
    │   │   ├── EmergencyBanner.tsx
    │   │   └── DisclaimerFooter.tsx
    │   ├── common/
    │   │   ├── ProtectedRoute.tsx
    │   │   ├── FirstUseModal.tsx
    │   │   └── ErrorBoundary.tsx
    │   └── ui/                # shadcn-generated primitives (button, dialog, scroll-area, ...)
    │
    ├── styles/
    │   └── globals.css        # Tailwind v4 entrypoint: @import "tailwindcss"; @theme { ... }
    │
    └── types/
        ├── api.ts             # Response shapes mirroring backend DTOs
        └── ws.ts              # WS envelope discriminated union
```

**Naming rules**:
- Components: `PascalCase.tsx`, default export named the same as the file.
- Hooks: `useFoo.ts`, named export.
- Stores: `fooStore.ts`, named export `useFooStore`.
- API callers: lowercase domain file, named exports (`fetchSessions`, `createSession`).
- One component per file. Co-locate styles in Tailwind classes — no per-component CSS files.

**Why `lib/` and `api/` are separate**: `lib/api.ts` is the *transport* (auth, retry, base URL). `api/*.ts` files are *domain callers* that import from `lib/api.ts`. Backend swap = touch `lib/`. Schema change = touch `api/`.

---

## 3. Backend Contract (Authoritative Snapshot)

Everything the frontend depends on lives in this section. If the backend changes, update here first.

### 3.1 Base URLs

- REST: `${VITE_API_BASE_URL}/api/v1` (dev: `http://localhost:8000`)
- WS: `${VITE_WS_URL}/api/v1/chat/ws/{session_id}?token=<access_token>` (dev: `ws://localhost:8000`)

Both pass through nginx in prod; the env vars resolve to the public origin.

### 3.2 Auth

| Action | Method | Path | Body | Returns |
|---|---|---|---|---|
| Start login | GET | `/auth/kakao/login` | — | `{ auth_url: string }` |
| Exchange code | POST | `/auth/kakao/callback?code=<code>` | — (code is a query param, not a JSON body) | `{ access_token: string }` + sets HttpOnly `refresh_token` cookie |
| Refresh | GET | `/auth/token/refresh` | — (cookie auto-sent) | `{ access_token: string }` |

Header on protected endpoints: `Authorization: Bearer <access_token>`.

### 3.3 Chat REST

| Method | Path | Returns |
|---|---|---|
| POST | `/chat/sessions` | `ChatSessionResponse` |
| GET | `/chat/sessions` | `ChatSessionResponse[]` |
| GET | `/chat/sessions/{id}/messages` | `{ messages: ChatMessageResponse[] }` |
| POST | `/chat/sessions/{id}/messages` | `{ user_message, assistant_message }` — Week 2 uses this synchronous REST endpoint (server aggregates LLM stream and returns once). WebSocket streaming moves to Week 3. |

```ts
// types/api.ts (mirror of backend DTOs)
export interface ChatSessionResponse {
  id: string;                  // uuid
  title: string;
  created_at: string;          // ISO
  updated_at: string;
}

export interface ChatMessageResponse {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  // Added by RAG/safety work in Week 1 (PLAN §3.3):
  sources?: Source[] | null;
  emergency_level?: "tier1" | "tier2" | "tier3" | null;
  rating?: 1 | -1 | null;      // Added in Week 3 (PLAN §5.2)
}

export interface Source {
  index: number;               // [1], [2] inline citation key
  title: string;
  source_type: "MFDS" | string;
  similarity: number;
  snippet: string;             // first ~200 chars of chunk
}
```

### 3.4 WebSocket Envelope

Server frames are JSON. Discriminated union on `type`:

```ts
// types/ws.ts
export type ServerFrame =
  | { type: "stream";    content: string }                              // token delta
  | { type: "done";      content: { full_text: string;
                                    sources: Source[];
                                    disclaimer: string;
                                    emergency_level: string | null } }
  | { type: "emergency"; content: { level: "tier1" | "tier2" | "tier3";
                                    phone: "119" | "1393" | "1339";
                                    message: string } }
  | { type: "refusal";   content: string }                              // moderation flagged
  | { type: "error";     content: string };

// Client → server: plain text. No envelope.
export type ClientFrame = string;
```

Lifecycle: open → send user message as plain text → receive 0..N `stream` frames → receive exactly one terminal frame (`done` | `emergency` | `refusal` | `error`). Then idle until next user input or `close`.

### 3.5 Users

`GET /users/me` → `UserInfoResponse` (id, email, name, ...). Used by `ProfileModal` (sidebar → "내 정보" 버튼). `DELETE /users/me` requires body `{ confirmation_text: "회원탈퇴합니다" }`. Exposed in Week 2 via `ProfileModal`; success → `authStore.clear()` + redirect to `/login`.

### 3.6 What we do NOT call in Week 2

`/guides/*`, `/ocr/*`. Endpoints exist; week 2 doesn't expose them. Don't write callers for them — adds dead code.

---

## 4. State Ownership

Three layers, each with a clear boundary. **Do not store the same data twice.**

### 4.1 Server state → TanStack Query

Anything that originates from the backend and can be refetched: session list, message history, current user profile.

```ts
// hooks/useSessions.ts
export const useSessions = () => useQuery({
  queryKey: ["sessions"],
  queryFn: fetchSessions,
  staleTime: 30_000,
});
```

Mutations (`createSession`, `deleteSession`) invalidate `["sessions"]`. Use optimistic updates for `createSession` so the new session appears in the sidebar before the POST returns.

### 4.2 Client state → Zustand

Anything that is purely local: tokens, in-flight WS buffer, UI flags.

```ts
// store/authStore.ts
interface AuthState {
  accessToken: string | null;
  user: UserInfo | null;
  hasSeenDisclaimer: boolean;
  setToken: (t: string) => void;
  clear: () => void;
}
```

```ts
// store/chatStore.ts
interface ChatState {
  currentSessionId: string | null;
  // Live stream buffer for the assistant message being composed *right now*.
  // Once `done` arrives, this is flushed and TanStack Query's message history is invalidated.
  streamingBuffer: string;
  streamingMessageId: number | null;   // matches a placeholder ID until the real message arrives
  emergency: { level: string; phone: string; message: string } | null;
}
```

**Persistence**: `authStore` persists `accessToken` and `hasSeenDisclaimer` to `localStorage` via `zustand/middleware/persist`. `chatStore` is in-memory only — reloading wipes the live stream buffer (the user can refetch history from REST).

**Security note**: storing the access token in `localStorage` accepts XSS risk in exchange for surviving page reload. The refresh token stays HttpOnly. This is the minimum acceptable for an MVP demo; a hardened build would move to in-memory + silent refresh on every page load. Document the tradeoff; do not silently change it.

### 4.3 React local state → `useState` / `useReducer`

Form inputs, hover state, modal open/close. Do not promote to Zustand unless two unrelated components both read it.

---

## 5. Auth Flow

```
[Login.tsx]
   │   user clicks "Kakao로 로그인"
   ▼
fetchKakaoLoginUrl()  ── GET /auth/kakao/login ──▶ { auth_url }
   │
   window.location.href = auth_url
   ▼
[Kakao OAuth consent screen]
   │
   redirect to /auth/kakao/callback?code=...
   ▼
[KakaoCallback.tsx]
   │   const code = useSearchParams().get("code")
   ▼
exchangeCode(code) ── POST /auth/kakao/callback ─▶ { access_token } + sets cookie
   │
   authStore.setToken(access_token)
   navigate("/chat")
```

**401 handling** (in `lib/api.ts`):

```ts
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const doFetch = (token: string | null) =>
    fetch(`${env.VITE_API_BASE_URL}/api/v1${path}`, {
      ...init,
      credentials: "include",   // for refresh cookie
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    });

  let res = await doFetch(useAuthStore.getState().accessToken);

  if (res.status === 401 && !path.startsWith("/auth/")) {
    const refreshed = await refreshAccessToken();   // GET /auth/token/refresh
    if (refreshed) {
      useAuthStore.getState().setToken(refreshed);
      res = await doFetch(refreshed);
    } else {
      useAuthStore.getState().clear();
      window.location.href = "/login";
      throw new Error("session expired");
    }
  }

  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json();
}
```

**One refresh in flight at a time**: guard `refreshAccessToken()` with a module-level promise so concurrent 401s deduplicate to a single refresh call.

---

## 6. WebSocket Layer

### 6.1 Lifecycle

```
mount Chat page
   │
   ▼
useChatSocket(sessionId, accessToken)
   │
   ▼
new WebSocket(`${VITE_WS_URL}/api/v1/chat/ws/${sessionId}?token=${accessToken}`)
   │
   ├─ onopen   → set status "connected"; flush any queued outgoing message
   ├─ onmessage(e) → JSON.parse → dispatch by envelope type
   │       ├─ "stream"    → chatStore.appendToBuffer(content)
   │       ├─ "done"      → chatStore.flushBuffer(); queryClient.invalidateQueries(["messages", sessionId])
   │       ├─ "emergency" → chatStore.setEmergency(content); abort buffer
   │       ├─ "refusal"   → chatStore.flushRefusal(content)
   │       └─ "error"     → toast.error(content); chatStore.abortBuffer()
   ├─ onclose  → schedule reconnect with exponential backoff + jitter (1s → 30s, cap)
   └─ onerror  → log; allow onclose to handle reconnect
```

### 6.2 Reconnection

Backoff: `min(30s, 2^attempt * 1s) * (0.5 + Math.random() * 0.5)`. Reset `attempt` to 0 on `onopen`. Cap at 30s. Stop reconnecting after 8 consecutive failures and show a "disconnected, click to retry" banner — silent infinite retry is worse than a visible failure.

**Token expiry mid-session**: if `onclose.code === 1008` (policy violation, sent by backend on JWT failure), do **not** reconnect blindly. Trigger `refreshAccessToken()` first, then reconnect with the new token. If refresh fails, log out.

### 6.3 Send path

```ts
const send = (text: string) => {
  if (ws.readyState !== WebSocket.OPEN) {
    pending.push(text);              // flushed on next onopen
    return;
  }
  // Optimistic: append a "user" bubble immediately via useOptimistic
  ws.send(text);
};
```

The user message is **not** echoed by the backend. The frontend renders it optimistically; the historical fetch will return the persisted version when the session is reopened.

---

## 7. Routing

```ts
// routes.tsx
export const routes = createBrowserRouter([
  { path: "/login", element: <Login /> },
  { path: "/auth/kakao/callback", element: <KakaoCallback /> },
  {
    element: <ProtectedRoute />,           // checks authStore.accessToken
    children: [
      { path: "/", element: <Navigate to="/chat" replace /> },
      { path: "/chat", element: <Chat /> },
      { path: "/chat/:sessionId", element: <Chat /> },
    ],
  },
  { path: "*", element: <NotFound /> },
]);
```

`ProtectedRoute` renders `<Outlet />` if authed, otherwise `<Navigate to="/login" replace />`. The first-use disclaimer modal is rendered *inside* `Chat`, not as a route — closing it sets `authStore.hasSeenDisclaimer = true`.

---

## 8. Error Handling

Three layers, in order:

1. **Network errors** (`lib/api.ts`) → throw `ApiError(status, body)`. TanStack Query surfaces them; mutations show a toast.
2. **WS errors** → handled in `useChatSocket`. Banner if disconnected; toast for transient `error` frames; emergency frames take over the UI regardless.
3. **Render errors** → top-level `<ErrorBoundary>` in `main.tsx`. Renders a "문제가 발생했습니다 — 새로고침" full-screen card. Does **not** automatically reload (could loop).

**What never gets a try/catch**: parsing a known-shape JSON envelope from the WS. If the backend sends garbage, that's a bug — let it throw and surface in the boundary.

**Toast library**: shadcn/ui's `sonner` integration. One toast provider in `App.tsx`.

---

## 9. Styling & Design Tokens (Skeleton)

Full design system is out of scope (PLAN §1 picked "architecture-focused" DESIGN.md). What's mandatory:

```css
/* src/styles/globals.css */
@import "tailwindcss";

@theme {
  /* Brand */
  --color-primary: oklch(0.55 0.18 250);    /* trust-blue, medical neutral */
  --color-danger:  oklch(0.55 0.22 25);     /* emergency banner */
  --color-warning: oklch(0.75 0.18 75);
  --color-success: oklch(0.65 0.15 145);

  /* Surfaces */
  --color-bg: oklch(0.99 0 0);
  --color-fg: oklch(0.20 0 0);
  --color-muted: oklch(0.60 0 0);

  /* Type */
  --font-sans: "Pretendard Variable", system-ui, sans-serif;

  /* Radii / spacing follow Tailwind defaults */
}
```

**Mandatory constraints** (PLAN §4.6):
- Touch targets ≥ 44×44px.
- Input bar `position: sticky; bottom: 0; padding-bottom: env(safe-area-inset-bottom);` to clear iOS Safari's home indicator.
- Manual breakpoints 360 / 768 / 1280.
- Emergency banner: `bg-danger text-white`, always visible above message scroll area, sticky top.
- WCAG 2.2 AA contrast on `--color-fg` against `--color-bg`. Verify with a checker, not by eye.

Component visual specs (sizes, exact spacing) are deferred to the post-MVP UI doc.

---

## 10. Environment Variables

```bash
# frontend/.env.example
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_KAKAO_REDIRECT_URI=http://localhost:3000/auth/kakao/callback
```

In prod, all three resolve to the same origin via nginx (`https://medi-mate.example.com` / `wss://...`). No `VITE_KAKAO_CLIENT_ID` on the frontend — the backend assembles the OAuth URL and returns it via `/auth/kakao/login`.

`lib/env.ts` validates these at module load:

```ts
import { z } from "zod";
const schema = z.object({
  VITE_API_BASE_URL: z.string().url(),
  VITE_WS_URL: z.string().regex(/^wss?:\/\//),
  VITE_KAKAO_REDIRECT_URI: z.string().url(),
});
export const env = schema.parse(import.meta.env);   // throws at boot if misconfigured
```

Fail-fast on missing config beats silent `undefined` in fetch URLs.

---

## 11. Build & Deploy

### 11.1 Local dev

```bash
cd frontend
pnpm install
pnpm dev          # vite dev server on :3000 (matches backend KAKAO_REDIRECT_URI)
```

Backend must be running separately (`docker compose up fastapi ai-worker redis postgres`). `FRONTEND_URL=http://localhost:3000` in backend env so CORS matches.

### 11.2 Production build

```dockerfile
# frontend/Dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build       # outputs dist/

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### 11.3 nginx config

```nginx
# frontend/nginx.conf — served by the frontend container itself
server {
  listen 80;
  root /usr/share/nginx/html;

  # Cache hashed assets aggressively, never cache index.html
  location /assets/ { expires 1y; add_header Cache-Control "public, immutable"; }
  location = /index.html { add_header Cache-Control "no-store"; }

  # SPA fallback
  location / { try_files $uri /index.html; }
}
```

The reverse-proxy nginx at the root level (`infra/nginx/default.conf`) routes `/api/v1/*` and `/api/v1/chat/ws/*` to the FastAPI container, and everything else to the frontend container. WebSocket needs the proxy upgrade headers:

```nginx
location /api/v1/chat/ws/ {
  proxy_pass http://fastapi:8000;
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  proxy_read_timeout 3600s;   # long-lived WS
}
```

### 11.4 docker-compose addition

```yaml
# docker-compose.yml — new service
frontend:
  build: ./frontend
  ports: ["5173:80"]   # or only expose via root nginx in prod
  depends_on: [fastapi]
```

---

## 12. Testing Strategy (Week 2 minimum)

Code correctness ≠ feature correctness. Tests cover the first; manual demo covers the second.

| Layer | Tool | What's covered |
|---|---|---|
| Unit | Vitest | `lib/api.ts` retry-on-401, `lib/ws.ts` envelope parser, `useChatSocket` reducer logic |
| Component | Vitest + Testing Library | `InputComposer` IME-composition guard, `EmergencyBanner` renders all three tiers, `MessageBubble` renders citations |
| Integration | — | **Skip**. No MSW, no Playwright in week 2. PLAN §6 demo scenarios are the integration test. |

**Hard requirement**: a Vitest unit for the WS envelope parser. Backend-shape drift is the most likely runtime bug.

---

## 13. Conventions

- **Imports**: absolute via `@/` (vite alias to `src/`). Sorted by Biome / Prettier — don't argue.
- **Default vs named exports**: components default-export; everything else named.
- **No `useEffect` for data fetching** — use TanStack Query. The only `useEffect` allowed is for genuine side effects (WS connect/disconnect, focus management).
- **No `any`**. Use `unknown` and narrow. The WS envelope union exists so you never need `any` for incoming frames.
- **Don't catch errors to log them and rethrow.** Either handle (return a fallback) or let them propagate.
- **Don't add a wrapper component named `XYZWrapper`.** If a component needs a wrapper, the component already exists.

---

## 14. Open Decisions (decide before week 2 starts)

1. **Biome vs ESLint+Prettier.** Biome is faster and simpler; ESLint has wider plugin support. No wrong answer — pick once, commit the config, don't revisit.
2. **`sonner` toast vs `shadcn` toast.** shadcn deprecated its in-house toast in favor of `sonner` in 2024. Use `sonner`.
3. **Pretendard via CDN vs self-host.** Self-host (`public/fonts/`) — no third-party DNS in the critical path, no privacy footprint.
4. **WebSocket reconnect on auth refresh.** Confirmed in §6.2 — close-code `1008` triggers refresh + reconnect.
5. **Where does the `[1]` `[2]` inline citation marker get clickable behavior?** Proposal: `react-markdown` `components.text` walks the text node, regex-replaces `[N]` with a `<button>` that scrolls to / highlights the corresponding `CitationCard`. Implement on Day 4 if time permits; skip for MVP otherwise.

Bring any of these to the user on Day 1 of week 2 if not already resolved.

---

## 15. Change Process

This file is the source of truth for *how* the frontend is structured. If you find yourself doing something that contradicts a section here, **update DESIGN.md in the same PR** that changes the code. A diff that touches `frontend/src/` without touching DESIGN.md (when it should) is incomplete.

PLAN.md owns *when*. DESIGN.md owns *how*. Backend contract drift = update §3 first, then the code that depends on it.
