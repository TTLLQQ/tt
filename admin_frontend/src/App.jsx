import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { Alert, Button, Card, Checkbox, Form, Input, InputNumber, Modal, Select, Space, Spin, Switch, Table, Tabs, Tag, message } from "antd";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ReactECharts from "echarts-for-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const client=axios.create({baseURL:"/api"});
client.interceptors.request.use(config=>{const token=localStorage.getItem("tt_admin_token");if(token)config.headers.Authorization=`Bearer ${token}`;return config;});
const err=e=>e.response?.data?.detail||e.message||"请求失败";
const text=v=>typeof v==="string"?v:JSON.stringify(v,null,2);
const COLORS=["#5145cd","#7b70e8","#b1aaff","#f5a78c","#52aa93"];

function Login({onLogin}) {
 const [busy,setBusy]=useState(false);
 const submit=async values=>{setBusy(true);try{const {data}=await client.post("/users/login",new URLSearchParams(values),{headers:{"Content-Type":"application/x-www-form-urlencoded"}});localStorage.setItem("tt_admin_token",data.access_token);const me=await client.get("/users/me");if(!me.data.is_admin){localStorage.removeItem("tt_admin_token");throw new Error("当前账号没有管理员权限");}onLogin(me.data);}catch(e){message.error(err(e));}finally{setBusy(false);}};
 return <main className="admin-login"><Card className="login-card"><div className="admin-brand">✦ <span>灵犀智能</span><Tag color="purple">ADMIN</Tag></div><h1>管理工作台</h1><p>登录以管理模型、工具和数字员工</p><Form layout="vertical" onFinish={submit}><Form.Item name="username" label="管理员账号" rules={[{required:true}]}><Input size="large" autoComplete="username"/></Form.Item><Form.Item name="password" label="密码" rules={[{required:true}]}><Input.Password size="large" autoComplete="current-password"/></Form.Item><Button type="primary" size="large" htmlType="submit" loading={busy} block>安全登录</Button></Form><small>仅管理员角色可访问；密码使用 bcrypt 校验。</small></Card></main>;
}

function AdminApp({me,onLogout}) {
 const [tab,setTab]=useState("overview"),[stats,setStats]=useState(null);
 useEffect(()=>{client.get("/admin/dashboard").then(({data})=>setStats(data)).catch(e=>message.error(err(e)));},[]);
 const tabs=[
  {key:"overview",label:"总览",children:<Overview stats={stats}/>},
  {key:"users",label:"用户管理",children:<Users/>},
  {key:"messages",label:"聊天信息",children:<Messages/>},
  {key:"assistant",label:"对话助手",children:<ChatAssistant/>},
  {key:"models",label:"大模型管理",children:<Models/>},
  {key:"tools",label:"工具管理",children:<Tools/>},
  {key:"employees",label:"数字员工",children:<Employees/>},
  {key:"analytics",label:"数据分析",children:<Analytics/>}
 ];
 return <div className="admin-shell"><aside className="admin-side"><div className="admin-brand">✦ <span>灵犀智能</span></div><div className="side-label">CONTROL CENTER</div>{tabs.map(item=><button key={item.key} className={tab===item.key?"side-active":""} onClick={()=>setTab(item.key)}>{item.label}</button>)}<div className="admin-side-bottom"><span className="online-mark"/>服务连接正常</div></aside><main className="admin-main"><header className="admin-top"><div><span className="crumb">管理中心 / </span><b>{tabs.find(item=>item.key===tab)?.label}</b></div><Space><Tag color="green">API ONLINE</Tag><span className="admin-user">{me.display_name||me.username}</span><Button onClick={onLogout}>退出</Button></Space></header><section className="admin-content">{tabs.find(item=>item.key===tab)?.children}</section></main></div>;
}

function Overview({stats}) {
 return <><Heading eyebrow="OVERVIEW" title="系统总览" sub="服务数据来自当前 SQLite 数据库"/><div className="stats-grid">{[["注册用户",stats?.users],["聊天室",stats?.rooms],["消息记录",stats?.messages],["工具调用",stats?.tool_calls]].map(([label,value])=><Card key={label} className="stat-card"><span>{label}</span><strong>{value??"—"}</strong><small>实时统计</small></Card>)}</div><Alert type="info" showIcon message="安全运行模式" description="生成的工具代码只保存为文本，不会执行。Function 调用仅允许注册的 Python 内置白名单工具。"/></>;
}

function Heading({eyebrow,title,sub,extra}){return <div className="section-heading"><div><small>{eyebrow}</small><h1>{title}</h1><p>{sub}</p></div>{extra}</div>;}

function Users(){
 const [items,setItems]=useState([]),[loading,setLoading]=useState(false);
 const load=useCallback(()=>{setLoading(true);client.get("/admin/users").then(({data})=>setItems(data)).catch(e=>message.error(err(e))).finally(()=>setLoading(false));},[]);
 useEffect(load,[load]);
 const columns=[{title:"ID",dataIndex:"id"},{title:"用户名",dataIndex:"username"},{title:"显示名称",dataIndex:"display_name"},{title:"角色",render:(_,r)=><Tag color={r.is_admin?"purple":"default"}>{r.is_admin?"管理员":"用户"}</Tag>},{title:"注册时间",dataIndex:"created_at",render:v=>new Date(v).toLocaleString()},{title:"操作",render:(_,r)=><Space><Button size="small" onClick={()=>client.patch(`/admin/users/${r.id}`,{is_admin:!r.is_admin}).then(load).catch(e=>message.error(err(e)))}>{r.is_admin?"取消管理员":"设为管理员"}</Button><Button danger size="small" onClick={()=>Modal.confirm({title:"删除用户？",content:"相关用户数据将按数据库约束清理。",onOk:()=>client.delete(`/admin/users/${r.id}`).then(load)})}>删除</Button></Space>}];
 return <><Heading eyebrow="ACCOUNT CONTROL" title="用户管理" sub="账号、角色与注册记录"/><Card><Table rowKey="id" loading={loading} columns={columns} dataSource={items}/></Card></>;
}

function Messages(){
 const [items,setItems]=useState([]),[loading,setLoading]=useState(false),[result,setResult]=useState(null);
 const load=useCallback(()=>{setLoading(true);client.get("/admin/messages").then(({data})=>setItems(data)).catch(e=>message.error(err(e))).finally(()=>setLoading(false));},[]);
 useEffect(load,[load]);
 const analyze=async()=>{try{const response=await fetch("/api/admin/analyze-sensitive",{method:"POST",headers:{Authorization:`Bearer ${localStorage.getItem("tt_admin_token")}`}});if(!response.ok){const body=await response.json();throw new Error(body.detail||"分析失败");}const reader=response.body.getReader(),decoder=new TextDecoder();let buffer="",finalResult=null;while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const blocks=buffer.split("\n\n");buffer=blocks.pop()||"";for(const block of blocks){const type=block.match(/^event: (.+)$/m)?.[1],raw=block.match(/^data: (.+)$/m)?.[1];if(type==="progress"&&raw)setResult(JSON.parse(raw));if(type==="done"&&raw)finalResult=JSON.parse(raw);}}if(finalResult)setResult(finalResult);load();}catch(e){message.error(e.message);}};
 const columns=[{title:"消息",dataIndex:"content",ellipsis:true},{title:"房间",dataIndex:"room_id"},{title:"发送者",dataIndex:"sender_id"},{title:"风险",dataIndex:"is_sensitive",render:v=><Tag color={v?"red":"green"}>{v?"敏感":"正常"}</Tag>},{title:"时间",dataIndex:"created_at",render:v=>new Date(v).toLocaleString()}];
 return <><Heading eyebrow="MESSAGE MODERATION" title="聊天信息管理" sub="检查消息记录并运行敏感信息扫描" extra={<Button type="primary" onClick={analyze}>运行敏感分析</Button>}/>{result&&<Alert type="info" message={`检查 ${result.checked} 条，标记 ${result.flagged} 条（${result.method}）`} closable/>}<Card style={{marginTop:16}}><Table rowKey="id" loading={loading} columns={columns} dataSource={items}/></Card></>;
}

function ChatAssistant(){
 const [question,setQuestion]=useState("统计每日聊天消息趋势"),[events,setEvents]=useState([]),[busy,setBusy]=useState(false);
 const run=async()=>{setBusy(true);setEvents([]);try{const response=await fetch("/api/chat-assistant/query",{method:"POST",headers:{"Content-Type":"application/json",Authorization:`Bearer ${localStorage.getItem("tt_admin_token")}`},body:JSON.stringify({question})});if(!response.ok){const detail=await response.json();throw new Error(detail.detail||"查询失败");}const reader=response.body.getReader(),decoder=new TextDecoder();let buffer="";while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const parts=buffer.split("\n\n");buffer=parts.pop()||"";for(const part of parts){const type=part.match(/^event: (.+)$/m)?.[1],data=part.match(/^data: (.+)$/m)?.[1];if(type&&data)setEvents(current=>[...current,{type,data:JSON.parse(data)}]);}}}catch(e){message.error(e.message);}finally{setBusy(false);}};
 const chart=events.find(e=>e.type==="chart_result")?.data;
 const summary=events.filter(e=>e.type==="content").map(e=>e.data.text).join("\n");
 const chartOption=chart&&chart.type==="pie"
  ? {tooltip:{trigger:"item"},series:[{type:"pie",radius:"65%",data:chart.labels.map((name,index)=>({name,value:chart.values[index]})),label:{color:"#25233a"}}]}
  : chart&&chart.type==="scatter"
   ? {tooltip:{trigger:"item"},xAxis:{type:"value",name:"序号"},yAxis:{type:"value"},series:[{type:"scatter",data:chart.values.map((value,index)=>[index,value]),itemStyle:{color:"#5145cd"}}]}
   : chart?{tooltip:{trigger:"axis"},grid:{left:42,right:20,top:24,bottom:48},xAxis:{type:"category",data:chart.labels,axisLabel:{rotate:chart.labels.length>6?30:0}},yAxis:{type:"value",minInterval:1},series:[{type:chart.type==="line"?"line":"bar",data:chart.values,smooth:chart.type==="line",itemStyle:{color:"#5145cd"},areaStyle:chart.type==="line"?{color:"#aaa1ff44"}:undefined}]}:null;
 return <><Heading eyebrow="NATURAL LANGUAGE ANALYTICS" title="对话助手" sub="提问统计问题，安全查询后流式返回图表与总结"/><Card><Space.Compact style={{width:"100%"}}><Input value={question} onChange={e=>setQuestion(e.target.value)} onPressEnter={run} placeholder="例如：统计每日聊天消息趋势"/><Button type="primary" loading={busy} onClick={run}>提问</Button></Space.Compact><div className="assistant-events">{events.map((item,index)=><div className="event-line" key={index}><Tag color={item.type.includes("result")?"green":"purple"}>{item.type}</Tag><code>{text(item.data)}</code></div>)}</div>{summary&&<div className="markdown-answer"><ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown></div>}{chart&&<div className="stream-chart"><h3>{chart.title}</h3><ReactECharts option={chartOption} style={{height:260}} notMerge/></div>}</Card></>;
}

function Models(){
 const [items,setItems]=useState([]),[form,setForm]=useState({name:"",provider:"openai-compatible",base_url:"",model_name:"",api_key:""}),[busy,setBusy]=useState(false);
 const load=useCallback(()=>client.get("/ai-agents/models").then(({data})=>setItems(data)).catch(e=>message.error(err(e))),[]);
 useEffect(load,[load]);
 const create=async()=>{setBusy(true);try{await client.post("/ai-agents/models",form);setForm({...form,name:"",model_name:"",api_key:""});message.success("模型配置已加密保存");load();}catch(e){message.error(err(e));}finally{setBusy(false);}};
 const columns=[{title:"名称",dataIndex:"name"},{title:"模型标识",dataIndex:"model_name"},{title:"接口地址",dataIndex:"base_url"},{title:"密钥",dataIndex:"api_key",render:()=> "已配置 · 不回显"},{title:"默认",dataIndex:"is_default",render:(value,row)=>value?<Tag color="green">默认</Tag>:<Button size="small" onClick={()=>client.post(`/ai-agents/models/${row.id}/default`).then(load).catch(e=>message.error(err(e)))}>设为默认</Button>},{title:"连接测试",render:(_,row)=><Button size="small" onClick={()=>client.post(`/ai-agents/models/${row.id}/test`).then(({data})=>message.success(data.response||"连接成功")).catch(e=>message.error(err(e)))}>测试</Button>}];
 return <><Heading eyebrow="MODEL PROVIDERS" title="大模型管理" sub="密钥加密存储，接口不返回明文"/><Card><div className="form-grid"><Input placeholder="配置名称" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/><Input placeholder="Base URL（OpenAI-compatible）" value={form.base_url} onChange={e=>setForm({...form,base_url:e.target.value})}/><Input placeholder="模型名称" value={form.model_name} onChange={e=>setForm({...form,model_name:e.target.value})}/><Input.Password placeholder="API Key" value={form.api_key} onChange={e=>setForm({...form,api_key:e.target.value})}/><Button type="primary" loading={busy} onClick={create}>新增模型</Button></div></Card><Card className="table-card"><Table rowKey="id" columns={columns} dataSource={items}/></Card></>;
}

function Tools(){
 const [items,setItems]=useState([]),[logs,setLogs]=useState([]),[name,setName]=useState(""),[description,setDescription]=useState("");
 const load=useCallback(()=>Promise.all([client.get("/ai-agents/tools"),client.get("/ai-agents/tools/logs")]).then(([a,b])=>{setItems(a.data);setLogs(b.data);}).catch(e=>message.error(err(e))),[]);
 useEffect(load,[load]);
 const add=async()=>{try{await client.post("/ai-agents/tools",{name,description:description||"待安全审核的自定义工具",parameters_schema:{type:"object",properties:{},additionalProperties:false},function_code:"",enabled:false});message.success("已添加为禁用元数据；执行前需由开发者接入白名单实现");setName("");load();}catch(e){message.error(err(e));}};
 const test=async item=>{const args=item.builtin_key==="calculator"?{expression:"(12+8)*2"}:item.builtin_key==="text_process"?{text:" Hello ",operation:"trim"}:item.builtin_key==="random_number"?{minimum:1,maximum:10}:{};try{const {data}=await client.post(`/ai-agents/tools/${item.id}/test`,{arguments:args});message.success(`工具结果：${text(data.result)}`);load();}catch(e){message.error(err(e));}};
 const generate=async()=>{try{const query=new URLSearchParams({name:name||"custom_tool",description:description||"安全的客服工具提案"});const response=await fetch(`/api/admin/generate-tool?${query}`,{headers:{Authorization:`Bearer ${localStorage.getItem("tt_admin_token")}`}});if(!response.ok){const body=await response.json();throw new Error(body.detail||"生成失败");}const reader=response.body.getReader(),decoder=new TextDecoder();let buffer="",proposal="";while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const blocks=buffer.split("\n\n");buffer=blocks.pop()||"";for(const block of blocks){const event=block.match(/^event: (.+)$/m)?.[1];const raw=block.match(/^data: (.+)$/m)?.[1];if(event==="content"&&raw)proposal+=JSON.parse(raw).text;if(event==="error"&&raw)throw new Error(JSON.parse(raw).detail);}}Modal.info({title:"AI 生成工具提案（不可执行）",width:680,content:<pre className="proposal">{proposal||"模型没有返回内容"}</pre>});}catch(e){message.error(e.message);}};
 const columns=[{title:"名称",dataIndex:"name"},{title:"说明",dataIndex:"description"},{title:"白名单实现",dataIndex:"builtin_key",render:v=>v||"无（仅元数据）"},{title:"启用",dataIndex:"enabled",render:(v,row)=><Switch checked={v} onChange={enabled=>client.patch(`/ai-agents/tools/${row.id}`,{enabled}).then(load).catch(e=>message.error(err(e)))}/>},{title:"测试",render:(_,row)=><Button size="small" disabled={!row.builtin_key} onClick={()=>test(row)}>执行测试</Button>}];
 return <><Heading eyebrow="FUNCTION TOOLS" title="工具管理" sub="只执行明确注册的内置白名单；AI 生成源代码永不执行"/><Alert type="warning" showIcon message="安全约束：没有 exec/eval 动态执行路径。新增自定义源代码只作为不可执行元数据保存。"/><Card className="table-card"><Space wrap><Input value={name} onChange={e=>setName(e.target.value)} placeholder="自定义工具标识" style={{width:190}}/><Input value={description} onChange={e=>setDescription(e.target.value)} placeholder="工具说明" style={{width:270}}/><Button type="primary" disabled={!name.trim()} onClick={add}>新增禁用工具</Button><Button disabled={!name.trim()} onClick={generate}>AI 生成提案（SSE）</Button></Space><Table rowKey="id" columns={columns} dataSource={items} style={{marginTop:18}}/></Card><Heading eyebrow="AUDIT" title="工具调用日志" sub="记录调用入参、结果、状态与耗时"/><Card><Table rowKey="id" size="small" dataSource={logs} columns={[{title:"工具 ID",dataIndex:"tool_id"},{title:"参数",dataIndex:"arguments",render:text},{title:"结果",dataIndex:"result",ellipsis:true},{title:"状态",dataIndex:"status",render:v=><Tag color={v==="ok"?"green":"red"}>{v}</Tag>},{title:"耗时",dataIndex:"duration_ms",render:v=>`${v} ms`}]}/></Card></>;
}

function Employees(){
 const [items,setItems]=useState([]),[models,setModels]=useState([]),[tools,setTools]=useState([]),[form,setForm]=useState({name:"",description:"",system_prompt:"",model_id:null,tool_ids:[]});
 const load=useCallback(()=>Promise.all([client.get("/ai-agents/employees"),client.get("/ai-agents/models"),client.get("/ai-agents/tools")]).then(([a,b,c])=>{setItems(a.data);setModels(b.data);setTools(c.data);}).catch(e=>message.error(err(e))),[]);
 useEffect(load,[load]);
 const create=async()=>{try{await client.post("/ai-agents/employees",form);setForm({...form,name:"",description:"",system_prompt:""});message.success("数字员工已创建");load();}catch(e){message.error(err(e));}};
 const gen=async()=>{try{const {data}=await client.post("/ai-agents/employees/generate-prompt",{name:form.name});setForm({...form,system_prompt:data.prompt});}catch(e){message.error(err(e));}};
 return <><Heading eyebrow="DIGITAL EMPLOYEES" title="数字员工管理" sub="关联模型与工具，生成或编辑员工系统提示词"/><Card><div className="form-grid"><Input placeholder="员工名称" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/><Input placeholder="职责说明" value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/><Select allowClear placeholder="绑定模型" value={form.model_id} onChange={model_id=>setForm({...form,model_id})} options={models.map(m=>({value:m.id,label:m.name}))}/><Select mode="multiple" placeholder="绑定白名单工具" value={form.tool_ids} onChange={tool_ids=>setForm({...form,tool_ids})} options={tools.filter(t=>t.builtin_key).map(t=>({value:t.id,label:t.name}))}/><Input.TextArea className="wide" rows={4} placeholder="系统提示词" value={form.system_prompt} onChange={e=>setForm({...form,system_prompt:e.target.value})}/><Space><Button onClick={gen}>AI 生成提示词</Button><Button type="primary" onClick={create}>创建数字员工</Button></Space></div></Card><div className="employee-cards">{items.map(item=><Card key={item.id} title={item.name} extra={<Switch checked={item.enabled} onChange={enabled=>client.patch(`/ai-agents/employees/${item.id}`,{enabled}).then(load).catch(e=>message.error(err(e)))}/>}><p>{item.description}</p><small>模型：{models.find(m=>m.id===item.model_id)?.name||"未绑定"} · 已绑定工具：{item.tool_ids?.length||0}</small><Button danger size="small" style={{float:"right"}} onClick={()=>client.delete(`/ai-agents/employees/${item.id}`).then(load).catch(e=>message.error(err(e)))}>删除</Button></Card>)}</div></>;
}

function Analytics(){
 const [data,setData]=useState(null);
 useEffect(()=>{client.get("/admin/analytics").then(({data})=>setData(data)).catch(e=>message.error(err(e)));},[]);
 return <><Heading eyebrow="DATA ANALYTICS" title="数据分析中心" sub="小时消息趋势、风险分布与工具调用统计"/><div className="chart-grid"><Card title="消息小时趋势"><ResponsiveContainer width="100%" height={280}><AreaChart data={data?.hourly||[]}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="hour"/><YAxis allowDecimals={false}/><Tooltip/><Area dataKey="count" stroke="#5145cd" fill="#bcb5ff77"/></AreaChart></ResponsiveContainer></Card><Card title="敏感消息分布"><ResponsiveContainer width="100%" height={280}><PieChart><Pie data={(data?.risk||[]).map(r=>({name:r.sensitive?"敏感":"正常",value:r.count}))} dataKey="value" nameKey="name" outerRadius={90} label>{(data?.risk||[]).map((_,i)=><Cell key={i} fill={COLORS[i%COLORS.length]}/>)}</Pie><Tooltip/></PieChart></ResponsiveContainer></Card><Card title="工具调用状态"><ResponsiveContainer width="100%" height={260}><BarChart data={data?.tool_calls||[]}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="status"/><YAxis allowDecimals={false}/><Tooltip/><Bar dataKey="count" fill="#5145cd" radius={[6,6,0,0]}/></BarChart></ResponsiveContainer></Card></div></>;
}

export default function App(){
 const [me,setMe]=useState(null),[checking,setChecking]=useState(true);
 useEffect(()=>{if(!localStorage.getItem("tt_admin_token")){setChecking(false);return;}client.get("/users/me").then(({data})=>{if(data.is_admin)setMe(data);else localStorage.removeItem("tt_admin_token");}).catch(()=>localStorage.removeItem("tt_admin_token")).finally(()=>setChecking(false));},[]);
 if(checking)return <div className="login-wait"><Spin size="large"/></div>;
 if(!me)return <Login onLogin={setMe}/>;
 const logout=()=>{localStorage.removeItem("tt_admin_token");setMe(null);};
 return <AdminApp me={me} onLogout={logout}/>;
}
