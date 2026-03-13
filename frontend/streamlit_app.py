import os
import base64
import json
from typing import Any, Optional

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def api_base_url() -> str:
    return (os.getenv("API_BASE_URL") or "http://localhost:8000").rstrip("/")


def _auth_headers(token: Optional[str]) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def api_request(
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    json: Any | None = None,
    files: Any | None = None,
    params: dict[str, Any] | None = None,
    timeout: int = 60,
):
    url = f"{api_base_url()}{path}"
    headers = {}
    headers.update(_auth_headers(token))

    resp = requests.request(
        method=method.upper(),
        url=url,
        headers=headers,
        json=json,
        files=files,
        params=params,
        timeout=timeout,
    )
    content_type = resp.headers.get("Content-Type", "")
    data: Any
    if "application/json" in content_type:
        try:
            data = resp.json()
        except Exception:
            data = {"detail": resp.text}
    else:
        data = {"detail": resp.text}
    return resp.status_code, data


def ensure_state():
    st.session_state.setdefault("access_token", "")
    st.session_state.setdefault("refresh_token", "")
    st.session_state.setdefault("user_email", "")
    st.session_state.setdefault("chat_session_id", "")


def _jwt_payload(token: str) -> dict[str, Any]:
    try:
        parts = (token or "").split(".")
        if len(parts) < 2:
            return {}
        payload_b64 = parts[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        raw = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def sidebar_me_panel():
    st.sidebar.subheader("Me")

    token = (st.session_state.get("access_token") or "").strip()
    if not token:
        st.sidebar.caption("Not logged in.")
        return

    payload = _jwt_payload(token)
    exp = payload.get("exp")
    exp_str = ""
    if isinstance(exp, (int, float)) and exp > 0:
        exp_str = str(exp)

    with st.sidebar.expander("Session", expanded=True):
        st.code(token[:40] + ("..." if len(token) > 40 else ""), language="text")
        if exp_str:
            st.caption(f"JWT exp (unix): `{exp_str}`")

    if st.sidebar.button("Refresh profile", key="btn_me_refresh"):
        st.session_state["me_profile_refresh"] = (st.session_state.get("me_profile_refresh") or 0) + 1

    _ = st.session_state.get("me_profile_refresh", 0)

    status_u, data_u = api_request("GET", "/api/organizations/users/", token=token)
    status_o, data_o = api_request("GET", "/api/organizations/organizations/", token=token)

    user_obj: dict[str, Any] | None = None
    if status_u == 200 and isinstance(data_u, list) and data_u:
        email = (st.session_state.get("user_email") or "").strip().lower()
        if email:
            user_obj = next((u for u in data_u if isinstance(u, dict) and (u.get("email") or "").lower() == email), None)
        user_obj = user_obj or (data_u[0] if isinstance(data_u[0], dict) else None)

    org_obj: dict[str, Any] | None = None
    if status_o == 200 and isinstance(data_o, list) and data_o:
        org_obj = data_o[0] if isinstance(data_o[0], dict) else None

    if user_obj:
        st.sidebar.caption(f"Email: `{user_obj.get('email','')}`")
        st.sidebar.caption(f"Role: `{user_obj.get('role','')}`")
        st.sidebar.caption(f"Org ID: `{user_obj.get('organization','')}`")
    else:
        st.sidebar.caption(f"User profile: HTTP {status_u}")

    if org_obj:
        st.sidebar.caption(f"Org: `{org_obj.get('name','')}`")
        st.sidebar.caption(f"Slug: `{org_obj.get('slug','')}`")
    else:
        st.sidebar.caption(f"Org info: HTTP {status_o}")


def section_auth():
    st.header("Auth")

    with st.expander("API settings", expanded=False):
        st.write(f"API base: `{api_base_url()}`")
        st.caption("Set `API_BASE_URL` env var if needed.")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Register Organization")
        org_name = st.text_input("Organization name", value="Acme Corp", key="reg_org_name")
        org_slug = st.text_input("Organization slug (optional)", value="acme", key="reg_org_slug")
        admin_email = st.text_input("Admin email", value="admin@acme.com", key="reg_admin_email")
        admin_password = st.text_input("Admin password", value="AdminPassw0rd!", type="password", key="reg_admin_password")

        if st.button("Register", type="primary", key="btn_register"):
            payload = {
                "organization_name": org_name,
                "admin_email": admin_email,
                "admin_password": admin_password,
            }
            if org_slug.strip():
                payload["organization_slug"] = org_slug.strip()
            status, data = api_request("POST", "/api/auth/register/", json=payload)
            st.write({"status": status, "data": data})

    with c2:
        st.subheader("Login (JWT)")
        email = st.text_input("Email", value=st.session_state.get("user_email") or "admin@acme.com", key="login_email")
        password = st.text_input("Password", value="", type="password", key="login_password")

        if st.button("Login", type="primary", key="btn_login"):
            status, data = api_request("POST", "/api/auth/login/", json={"email": email, "password": password})
            if status == 200 and isinstance(data, dict):
                st.session_state["access_token"] = data.get("access", "") or ""
                st.session_state["refresh_token"] = data.get("refresh", "") or ""
                st.session_state["user_email"] = email
            st.write({"status": status, "data": data})

        token_preview = (st.session_state.get("access_token") or "")[:24]
        st.caption(f"Current access token: `{token_preview}{'...' if token_preview else ''}`")
        if st.button("Logout", key="btn_logout"):
            st.session_state["access_token"] = ""
            st.session_state["refresh_token"] = ""
            st.session_state["chat_session_id"] = ""
            st.success("Logged out.")


def section_invites():
    st.header("Invitations")
    token = st.session_state.get("access_token") or ""
    if not token:
        st.warning("Login first (Auth section).")
        return

    st.subheader("Create invite (org admin)")
    email = st.text_input("Invitee email", value="user1@acme.com", key="invite_email")
    role = st.selectbox("Role", options=["member", "admin"], index=0, key="invite_role")
    expires_in_days = st.number_input("Expires in days", min_value=1, max_value=30, value=7, step=1, key="invite_expires")

    if st.button("Create invitation", type="primary", key="btn_invite_create"):
        status, data = api_request(
            "POST",
            "/api/organizations/invitations/",
            token=token,
            json={"email": email, "role": role, "expires_in_days": int(expires_in_days)},
        )
        st.write({"status": status, "data": data})
        if status == 201 and isinstance(data, dict) and data.get("token"):
            st.code(data["token"], language="text")

    st.divider()

    st.subheader("List invitations")
    if st.button("Refresh invitations", key="btn_invite_list"):
        status, data = api_request("GET", "/api/organizations/invitations/", token=token)
        st.write({"status": status, "data": data})

    st.divider()
    st.subheader("Accept invitation (public)")
    inv_token = st.text_input("Invitation token", value="", key="accept_token")
    new_password = st.text_input("Set password", value="", type="password", key="accept_password")
    if st.button("Accept invitation", type="primary", key="btn_accept"):
        status, data = api_request(
            "POST",
            "/api/auth/invitations/accept/",
            json={"token": inv_token.strip(), "password": new_password},
        )
        st.write({"status": status, "data": data})


def section_documents():
    st.header("Documents")
    token = st.session_state.get("access_token") or ""
    if not token:
        st.warning("Login first (Auth section).")
        return

    st.subheader("Upload (org admin)")
    uploaded = st.file_uploader("Choose a policy document (.pdf, .docx, .txt)", type=["pdf", "docx", "txt"])
    if st.button("Upload", type="primary", disabled=uploaded is None, key="btn_upload"):
        files = {"file": (uploaded.name, uploaded.getvalue())}
        status, data = api_request("POST", "/api/documents/documents/", token=token, files=files)
        st.write({"status": status, "data": data})
        st.caption("Processing happens async (Celery). Wait a few seconds then search.")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("List documents")
        if st.button("Refresh documents", key="btn_docs_list"):
            status, data = api_request("GET", "/api/documents/documents/", token=token)
            st.write({"status": status, "data": data})

    with c2:
        st.subheader("List chunks")
        if st.button("Refresh chunks", key="btn_chunks_list"):
            status, data = api_request("GET", "/api/documents/document-chunks/", token=token)
            st.write({"status": status, "data": data})

    st.divider()

    st.subheader("Search (org members)")
    query = st.text_input("Query", value="What is our annual leave policy?", key="search_query")
    if st.button("Search", type="primary", key="btn_search"):
        status, data = api_request("POST", "/api/documents/search/", token=token, json={"query": query})
        st.write({"status": status, "data": data})


def section_chat():
    st.header("Chat")
    token = st.session_state.get("access_token") or ""
    if not token:
        st.warning("Login first (Auth section).")
        return

    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("Create session")
        title = st.text_input("Title (optional)", value="HR policies", key="chat_title")
        if st.button("Create chat session", type="primary", key="btn_chat_create"):
            status, data = api_request("POST", "/api/chat/sessions/", token=token, json={"title": title})
            st.write({"status": status, "data": data})
            if status == 200 and isinstance(data, dict) and data.get("session_id"):
                st.session_state["chat_session_id"] = data["session_id"]

    with c2:
        st.subheader("Current session")
        sid = st.text_input("Session ID", value=st.session_state.get("chat_session_id") or "", key="chat_sid")
        st.session_state["chat_session_id"] = sid.strip()

        if sid.strip() and st.button("Load messages", key="btn_chat_load"):
            status, data = api_request("GET", f"/api/chat/sessions/{sid.strip()}/", token=token)
            st.write({"status": status, "data": data})

    st.divider()

    sid = (st.session_state.get("chat_session_id") or "").strip()
    if not sid:
        st.info("Create a session first.")
        return

    st.subheader("Send message")
    content = st.text_area("Message", value="What is our annual leave policy?", height=120, key="chat_msg")
    top_k = st.slider("top_k", min_value=1, max_value=20, value=5, step=1, key="chat_topk")
    history_max_messages = st.slider("history_max_messages", min_value=0, max_value=50, value=20, step=1, key="chat_hist")

    if st.button("Send", type="primary", key="btn_chat_send"):
        status, data = api_request(
            "POST",
            f"/api/chat/sessions/{sid}/messages/",
            token=token,
            json={"content": content, "top_k": int(top_k), "history_max_messages": int(history_max_messages)},
        )
        st.write({"status": status, "data": data})


def main():
    ensure_state()

    st.set_page_config(page_title="Enterprise RAG SaaS (MVP)", layout="wide")
    st.title("Enterprise RAG SaaS (MVP)")
    st.caption("Org-scoped document upload + RAG chat. Uses the existing Django API.")

    sidebar_me_panel()

    section = st.sidebar.selectbox(
        "Section",
        options=["Auth", "Invitations", "Documents", "Chat"],
        index=0,
    )

    if section == "Auth":
        section_auth()
    elif section == "Invitations":
        section_invites()
    elif section == "Documents":
        section_documents()
    else:
        section_chat()


if __name__ == "__main__":
    main()
