import React,{useEffect,useState} from "react";
import {createRoot} from "react-dom/client";
import {Bot,Play,Plus,ShieldCheck,Code2,TestTube2,ClipboardCheck} from "lucide-react";
import "./styles.css";

const API="http://127.0.0.1:8000/api";

function App(){
 const [projects,setProjects]=useState([]),[projectId,setProjectId]=useState(""),[name,setName]=useState(""),[task,setTask]=useState(""),[code,setCode]=useState(""),[result,setResult]=useState(null),[loading,setLoading]=useState(false);
 const load=()=>fetch(API+"/projects").then(r=>r.json()).then(setProjects);
 useEffect(load,[]);
 async function createProject(){if(!name.trim())return;await fetch(API+"/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name,description:"ForgeAI engineering workspace"})});setName("");load();}
 async function run(){if(!projectId||!task.trim())return;setLoading(true);const r=await fetch(API+"/runs",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({project_id:Number(projectId),task,code})});setResult(await r.json());setLoading(false);}
 return <div className="app"><aside><div className="brand"><Bot/> ForgeAI</div><p className="muted">AI Software Engineering Workspace</p><div className="side-title">Projects</div>{projects.map(p=><button className="project" key={p.id} onClick={()=>setProjectId(String(p.id))}>{p.name}<small>#{p.id}</small></button>)}<div className="new"><input value={name} onChange={e=>setName(e.target.value)} placeholder="New project"/><button onClick={createProject}><Plus size={16}/> Create</button></div></aside>
 <main><header><div><h1>Engineering Command Center</h1><p>Coordinate planning, development, testing, security and review.</p></div><span className="badge">5 Agents</span></header>
 <section className="panel"><label>Project ID</label><input value={projectId} onChange={e=>setProjectId(e.target.value)} placeholder="Create/select a project"/><label>Engineering task</label><input value={task} onChange={e=>setTask(e.target.value)} placeholder="Example: Add JWT authentication"/><label>Source code for analysis <span>(optional)</span></label><textarea value={code} onChange={e=>setCode(e.target.value)} placeholder="Paste Python code here..."/><button className="run" onClick={run} disabled={loading}><Play size={17}/>{loading?"Running agents...":"Run multi-agent workflow"}</button></section>
 <section className="agents">{[[Bot,"Planner","Decompose requirement"],[Code2,"Developer","Implementation strategy"],[TestTube2,"Tester","Test scenarios"],[ShieldCheck,"Security","Static security scan"],[ClipboardCheck,"Reviewer","Final engineering verdict"]].map(([I,n,d])=><div className="agent" key={n}><I/><b>{n}</b><small>{d}</small></div>)}</section>
 {result&&<section className="panel result"><div className="result-head"><h2>Workflow Result</h2><strong className={result.result.final_review.verdict==="APPROVE"?"ok":"warn"}>{result.result.final_review.verdict}</strong></div>{result.result.agents.map(a=><details key={a.agent}><summary>{a.agent}</summary><pre>{JSON.stringify(a,null,2)}</pre></details>)}</section>}
 </main></div>
}
createRoot(document.getElementById("root")).render(<App/>);
