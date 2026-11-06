import { useEffect, useMemo, useRef, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { Button, Card, Checkbox, Empty, Input, Modal, Spin, message } from "antd";
import { api } from "./api";
import { useAuth } from "./store";

const EMOJI = [
  ...Array.from({ length: 80 }, (_, i) => String.fromCodePoint(0x1f600 + i)),
  ...Array.from({ length: 60 }, (_, i) => String.fromCodePoint(0x1f680 + i)),
  ...Array.from({ length: 60 }, (_, i) => String.fromCodePoint(0x1f900 + i)),
];
const IMAGE_EMOTES = ["1f970", "1f92f", "1f389", "1f44d", "1f525", "1f973", "1f496", "1f602"].map(
  (code) => `https://cdn.jsdelivr.net/gh/jdecked/twemoji@17.0.2/assets/72x72/${code}.png`,
);
const cleanImageUrl = (value) => {
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
};

function AuthPage() {
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ username: "", password: "", display_name: "" });
  const { setAuth } = useAuth();
  const navigate = useNavigate();

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      if (register) await api.post("/users/register", form);
      const body = new URLSearchParams({ username: form.username, password: form.password });
      const login = await api.post("/users/login", body, { headers: { "Content-Type": "application/x-www-form-urlencoded" } });
      const me = await api.get("/users/me", { headers: { Authorization: `Bearer ${login.data.access_token}` } });
      setAuth(login.data.access_token, me.data);
      navigate(location.pathname === "/login" ? "/" : location.pathname);
    } catch (error) {
      message.error(error.response?.data?.detail || "登录失败，请检查账号信息");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-art">
        <div className="orb orb-one" />
        <div className="orb orb-two" />
        <div className="art-copy">
          <span className="eyebrow">LINGXI · AI SERVICE</span>
          <h1>让每一次对话<br />都有智慧回应</h1>
          <p>智能协作，温暖沟通。</p>
        </div>
        <div className="art-glass">✦ &nbsp; AI 数字员工 · 随时为你服务</div>
      </section>
      <section className="auth-panel">
        <div className="auth-box">
          <Link className="logo" to="/">✦ <span>灵犀智能</span></Link>
          <h2>{register ? "创建你的账号" : "欢迎回来"}</h2>
          <p className="muted">{register ? "注册后即可创建聊天室并邀请数字员工" : "登录后继续你的智能协作"}</p>
          <form onSubmit={submit}>
            {register && <Input size="large" placeholder="显示名称" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />}
            <Input size="large" placeholder="用户名（至少 3 位）" autoComplete="username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
            <Input.Password size="large" placeholder="密码（至少 10 位）" autoComplete={register ? "new-password" : "current-password"} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
            <Button type="primary" size="large" htmlType="submit" loading={busy} block>{register ? "注册并登录" : "登录"}</Button>
          </form>
          <div className="auth-toggle">{register ? "已有账号？" : "还没有账号？"} <button onClick={() => setRegister(!register)}>{register ? "立即登录" : "免费注册"}</button></div>
          <p className="safe-caption">凭据使用 bcrypt 散列 · HTTPS 请由部署网关提供</p>
        </div>
      </section>
    </main>
  );
}

function JoinPage() {
  const { shareLink } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState("正在验证分享链接…");

  useEffect(() => {
    api.post(`/chatrooms/join/${encodeURIComponent(shareLink)}`)
      .then(({ data }) => {
        setStatus(`已加入「${data.name}」`);
        setTimeout(() => navigate(`/room/${data.room_id}`), 500);
      })
      .catch((error) => setStatus(error.response?.data?.detail || "分享链接无效或已过期"));
  }, [shareLink, navigate]);

  return <div className="center-screen"><Card><Spin />&nbsp; {status}<p><Link to="/">返回工作台</Link></p></Card></div>;
}

function Shell() {
  const { token, user, setUser, logout } = useAuth();
  const navigate = useNavigate();
  const { roomId } = useParams();
  const [rooms, setRooms] = useState([]);
  const [friends, setFriends] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [roomEmployees, setRoomEmployees] = useState([]);
  const [members, setMembers] = useState([]);
  const [activeRoom, setActiveRoom] = useState(null);
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [membersOpen, setMembersOpen] = useState(false);
  const [roomName, setRoomName] = useState("新的聊天室");
  const [selectedFriends, setSelectedFriends] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [draft, setDraft] = useState("");
  const [showEmoji, setShowEmoji] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const socketRef = useRef(null);
  const listRef = useRef(null);
  const partialMention = draft.match(/(?:^|\s)@([^\s]*)$/)?.[1];
  const employeeMentions = useMemo(
    () => partialMention === undefined ? [] : roomEmployees.filter((employee) => employee.name.startsWith(partialMention)),
    [partialMention, roomEmployees],
  );

  const refresh = async () => {
    const [me, roomData, friendData, employeeData] = await Promise.all([
      api.get("/users/me"), api.get("/chatrooms"), api.get("/users/friends"), api.get("/ai-agents/public-employees"),
    ]);
    setUser(me.data);
    setRooms(roomData.data);
    setFriends(friendData.data);
    setEmployees(employeeData.data);
  };

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    refresh().catch((error) => message.error(error.response?.data?.detail || "加载失败")).finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    if (roomId && rooms.length) {
      const selected = rooms.find((room) => room.id === Number(roomId));
      if (selected) setActiveRoom(selected);
    }
  }, [roomId, rooms]);

  useEffect(() => {
    if (!activeRoom || !token || !user) return undefined;
    setMessages([]);
    Promise.all([
      api.get(`/chatrooms/${activeRoom.id}/messages`),
      api.get(`/chatrooms/${activeRoom.id}/employees`),
      api.get(`/chatrooms/${activeRoom.id}/members`),
    ]).then(([history, roomStaff, roomMembers]) => {
      setMessages(history.data);
      setRoomEmployees(roomStaff.data);
      setMembers(roomMembers.data);
    }).catch((error) => message.error(error.response?.data?.detail || "加载聊天室失败"));
    const wsProtocol = location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${wsProtocol}://${location.host}/ws/chat/${activeRoom.id}/${user.id}?token=${encodeURIComponent(token)}`);
    socketRef.current = socket;
    socket.onmessage = (event) => {
      try {
        const item = JSON.parse(event.data);
        if (item.id) setMessages((current) => current.some((existing) => existing.id === item.id) ? current : [...current, item]);
      } catch {
        message.error("收到无法识别的实时消息");
      }
    };
    return () => { socket.close(); socketRef.current = null; };
  }, [activeRoom?.id, token, user?.id]);

  useEffect(() => { listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" }); }, [messages]);
  if (!token) return <AuthPage />;
  if (loading) return <div className="center-screen"><Spin size="large" /></div>;

  const createRoom = async () => {
    try {
      const { data } = await api.post("/chatrooms", { name: roomName, friend_ids: selectedFriends, employee_ids: selectedEmployees });
      setCreateOpen(false);
      setSelectedFriends([]);
      setSelectedEmployees([]);
      await refresh();
      setActiveRoom({ id: data.id, name: data.name, owner_id: user.id });
      navigate(`/room/${data.id}`);
      message.success("聊天室已创建");
    } catch (error) { message.error(error.response?.data?.detail || "创建失败"); }
  };

  const askEmployee = async (employee, content = draft) => {
    if (!activeRoom) return message.warning("请先选择聊天室");
    const question = content.replace(new RegExp(`^@${employee.name}\\s*`), "").trim();
    if (!question) return message.info("请在 @员工名称 后输入问题");
    setDraft("");
    try { await api.post(`/chatrooms/${activeRoom.id}/employee_reply`, { employee_id: employee.id, content: question }); }
    catch (error) { message.error(error.response?.data?.detail || "数字员工暂不可用"); }
  };

  const send = async (type = "text", content = draft) => {
    if (!activeRoom || !content.trim()) return;
    if (type === "text") {
      const agent = roomEmployees.find((employee) => content.startsWith(`@${employee.name}`));
      if (agent) return askEmployee(agent, content);
    }
    try {
      await api.post(`/chatrooms/${activeRoom.id}/messages`, { content: content.trim(), message_type: type });
      setDraft("");
    } catch (error) { message.error(error.response?.data?.detail || "发送失败"); }
  };

  const chooseEmployee = (employee) => {
    setDraft((current) => current.replace(/(^|\s)@[^\s]*$/, `$1@${employee.name} `));
  };
  const share = async () => {
    try {
      const { data } = await api.post(`/chatrooms/${activeRoom.id}/share`);
      await navigator.clipboard.writeText(`${location.origin}/join/${data.share_link}`);
      message.success("分享链接已复制");
    } catch { message.error("复制失败"); }
  };
  const search = async (value) => {
    setQuery(value);
    if (value.trim().length < 2) { setSearchResults([]); return; }
    try { setSearchResults((await api.get("/users/search", { params: { q: value } })).data); } catch { setSearchResults([]); }
  };
  const doSearchAdd = async (target) => {
    try {
      await api.post(`/users/friends/${target.id}`);
      await api.post(`/chatrooms/${activeRoom.id}/members/${target.id}`);
      message.success("已添加联系人和群成员");
      setSearchResults([]);
      setQuery("");
      const { data } = await api.get(`/chatrooms/${activeRoom.id}/members`);
      setMembers(data);
      refresh();
    } catch (error) { message.error(error.response?.data?.detail || "添加失败"); }
  };
  const removeMember = async (member) => {
    try {
      await api.delete(`/chatrooms/${activeRoom.id}/members/${member.id}`);
      setMembers((current) => current.filter((item) => item.id !== member.id));
      message.success("成员已移除");
    } catch (error) { message.error(error.response?.data?.detail || "移除失败"); }
  };
  const openPrivateRoom = async (friendId) => {
    try {
      const { data } = await api.post(`/chatrooms/private/${friendId}`);
      await refresh();
      setActiveRoom(data);
      navigate(`/room/${data.id}`);
    } catch (error) { message.error(error.response?.data?.detail || "创建私聊失败"); }
  };
  const updateProfile = async (event) => {
    event.preventDefault();
    try {
      const display_name = new FormData(event.currentTarget).get("display_name");
      const { data } = await api.patch("/users/profile", { display_name });
      setUser(data);
      setProfileOpen(false);
      message.success("资料已保存");
    } catch (error) { message.error(error.response?.data?.detail || "保存失败"); }
  };

  return (
    <div className="workspace">
      <aside className="rail">
        <div className="logo-mark">✦</div><button className="rail-active">◉</button>
        <button onClick={() => document.querySelector(".friend-list")?.scrollIntoView({ behavior: "smooth" })}>♧</button>
        {user?.is_admin && <button title="打开管理端" onClick={() => window.open("http://localhost:5174", "_blank", "noopener,noreferrer")}>⚙</button>}
        <div className="rail-bottom"><button onClick={() => { logout(); setUser(null); }}>↪</button></div>
      </aside>

      <aside className="left-panel">
        <div className="left-header"><div><span className="eyebrow">WORKSPACE</span><h2>灵犀智能</h2></div><Button type="primary" shape="circle" onClick={() => setCreateOpen(true)}>＋</Button></div>
        <div className="user-self"><span className="avatar">{(user?.display_name || user?.username || "我").slice(0, 1)}</span><div><b>{user?.display_name || user?.username}</b><small>已登录</small></div><button onClick={() => setProfileOpen(true)}>···</button></div>
        <div className="list-heading">最近会话 <span>{rooms.length}</span></div>
        <div className="room-list">{rooms.map((room) => <button key={room.id} className={`room-row ${activeRoom?.id === room.id ? "selected" : ""}`} onClick={() => { setActiveRoom(room); navigate(`/room/${room.id}`); }}><span className="room-avatar">{room.is_group ? "▦" : "◉"}</span><span className="room-meta"><b>{room.name}</b><small>打开会话查看消息</small></span></button>)}</div>
        <div className="list-heading contacts-title">联系人 <span>{friends.length}</span></div>
        <div className="friend-list">{friends.map((friend) => <div key={friend.id} className="friend-row"><span className="avatar small">{(friend.remark || friend.user.display_name || friend.user.username).slice(0, 1)}</span><span>{friend.remark || friend.user.display_name || friend.user.username}</span><button onClick={() => openPrivateRoom(friend.user.id)}>聊</button></div>)}</div>
      </aside>

      <main className="chat-main">
        <header className="chat-top">
          <div><h2>{activeRoom?.name || "选择一个聊天室"}</h2><small>{activeRoom ? "实时消息 · WebSocket" : "创建聊天室开始协作"}</small></div>
          {activeRoom && <div className="top-buttons"><Input size="small" placeholder="搜索用户名添加成员" value={query} onChange={(event) => search(event.target.value)} style={{ width: 190 }} /><Button onClick={share}>分享链接</Button><Button onClick={() => setMembersOpen(true)}>成员 {members.length}</Button></div>}
        </header>
        {searchResults.length > 0 && <div className="search-popover">{searchResults.map((item) => <button key={item.id} onClick={() => doSearchAdd(item)}>{item.display_name || item.username}<span>+ 加入群聊</span></button>)}</div>}
        {activeRoom ? <>
          <section className="message-list" ref={listRef}>
            {messages.length ? messages.map((item) => <article key={item.id} className={`message-bubble ${item.sender_id === user?.id ? "mine" : ""}`}><span className="avatar small">{item.sender_id < 0 ? "✦" : item.sender_id === user?.id ? "我" : "友"}</span><div><small>{item.sender_id < 0 ? roomEmployees.find((employee) => employee.id === -item.sender_id)?.name || "数字员工" : item.sender_id === user?.id ? "我" : members.find((member) => member.id === item.sender_id)?.display_name || "成员"} · {new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small>{item.type === "image" ? <img className="chat-image" src={cleanImageUrl(item.content)} alt="聊天图片" /> : <p>{item.content}</p>}</div></article>) : <Empty description="发送第一条消息，开始对话" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </section>
          <footer className="composer-wrap">
            {employeeMentions.length > 0 && <div className="mention-menu">{employeeMentions.map((employee) => <button key={employee.id} onClick={() => chooseEmployee(employee)}>✦ {employee.name}<small>{employee.description}</small><span>选择</span></button>)}</div>}
            {showEmoji && <div className="emoji-panel">{EMOJI.map((emoji, index) => <button key={`${emoji}-${index}`} onClick={() => { setDraft((current) => current + emoji); setShowEmoji(false); }}>{emoji}</button>)}<p className="emote-images">{IMAGE_EMOTES.map((url) => <button key={url} onClick={() => { setShowEmoji(false); send("image", url); }}><img src={url} alt="表情图片" loading="lazy" /></button>)}</p></div>}
            <div className="composer-tools"><button onClick={() => setShowEmoji(!showEmoji)}>☺ 表情</button><button onClick={() => { const url = window.prompt("输入 HTTPS 图片地址"); if (url && cleanImageUrl(url)) send("image", cleanImageUrl(url)); else if (url) message.warning("仅支持 HTTP/HTTPS 图片链接"); }}>▧ 图片</button><span>输入 @唤起本房间数字员工</span></div>
            <div className="input-row"><Input.TextArea value={draft} onChange={(event) => setDraft(event.target.value)} onPressEnter={(event) => { if (!event.shiftKey) { event.preventDefault(); send(); } }} autoSize={{ minRows: 1, maxRows: 4 }} placeholder="输入消息，按 Enter 发送…" maxLength={10000} /><Button type="primary" onClick={() => send()}>发送</Button></div>
          </footer>
        </> : <div className="welcome"><div className="welcome-icon">✦</div><h1>让对话，从容发生</h1><p>选择一个聊天室，或创建新群聊并邀请数字员工加入。</p><Button type="primary" onClick={() => setCreateOpen(true)}>创建聊天室</Button></div>}
      </main>

      <Modal title="创建群聊" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={createRoom} okText="创建">
        <label className="field-label">聊天室名称</label><Input value={roomName} onChange={(event) => setRoomName(event.target.value)} maxLength={100} />
        <label className="field-label">选择好友</label><Checkbox.Group value={selectedFriends} onChange={setSelectedFriends} options={friends.map((friend) => ({ label: friend.remark || friend.user.display_name || friend.user.username, value: friend.user.id }))} />
        <label className="field-label">邀请数字员工</label><Checkbox.Group value={selectedEmployees} onChange={setSelectedEmployees} options={employees.map((employee) => ({ label: employee.name, value: employee.id }))} />
      </Modal>
      <Modal title="聊天室成员" open={membersOpen} onCancel={() => setMembersOpen(false)} footer={null}>
        {members.map((member) => <div className="member-row" key={member.id}><span>{member.display_name || member.username}</span>{member.id === activeRoom?.owner_id && <span className="owner-tag">群主</span>}{activeRoom?.owner_id === user?.id && member.id !== user?.id && <Button danger size="small" onClick={() => removeMember(member)}>移除</Button>}</div>)}
      </Modal>
      <Modal title="个人资料" open={profileOpen} onCancel={() => setProfileOpen(false)} footer={null}>
        <form onSubmit={updateProfile}><label className="field-label">显示名称</label><Input name="display_name" defaultValue={user?.display_name} maxLength={80} /><Button type="primary" htmlType="submit" style={{ marginTop: 16 }}>保存资料</Button></form>
        <Button danger onClick={() => { logout(); setUser(null); }} style={{ marginTop: 12 }}>退出登录</Button>
      </Modal>
    </div>
  );
}

function ProtectedShell() {
  const { token } = useAuth();
  return token ? <Shell /> : <AuthPage />;
}

function JoinRoute() {
  const { token } = useAuth();
  return token ? <JoinPage /> : <AuthPage />;
}

export default function App() {
  const { token } = useAuth();
  return <Routes>
    <Route path="/login" element={token ? <Navigate to="/" /> : <AuthPage />} />
    <Route path="/join/:shareLink" element={<JoinRoute />} />
    <Route path="/room/:roomId" element={<ProtectedShell />} />
    <Route path="/contacts" element={<ProtectedShell />} />
    <Route path="*" element={<ProtectedShell />} />
  </Routes>;
}
