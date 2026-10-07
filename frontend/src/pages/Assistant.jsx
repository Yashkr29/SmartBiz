import {useEffect,useRef,useState} from 'react'
import {Send,Sparkles} from 'lucide-react'
import {api,errMsg} from '../api.js'

const badge={llm:'AI · live data',basic:'Basic mode · live data',error:'Not answered'}
const chips=['Who owes me the most?','Which products are low on stock?','What is my total pending amount?','Which orders are still in production?','How much did I spend on expenses this month?']

export default function Assistant(){
  const [msgs,setMsgs]=useState([{r:'ai',t:'Ask me anything about your orders, customers, stock, payments or expenses.'}])
  const [q,setQ]=useState(''),[busy,setBusy]=useState(false),end=useRef()
  useEffect(()=>{end.current?.scrollIntoView({behavior:'smooth',block:'end'})},[msgs,busy])

  const send=async t=>{
    t=t.trim();if(!t||busy)return
    setMsgs(m=>[...m,{r:'me',t}]);setQ('');setBusy(true)
    let reply
    try{const {data}=await api.post('/ai/ask',{question:t},{timeout:40000});reply={r:'ai',t:data.answer,sql:data.sql,rows:data.rows,src:data.mode}}
    catch(e){reply={r:'ai',t:errMsg(e),src:'error'}}
    setMsgs(m=>[...m,reply]);setBusy(false)
  }
  return(<div className="space-y-5"><h1 className="text-2xl font-extrabold">Ask SmartBiz</h1>
    <div className="rounded-3xl bg-white/85 shadow-sm shadow-sky-200/60 p-5 h-[55vh] overflow-y-auto flex flex-col gap-4" aria-live="polite">
      {msgs.map((m,i)=>(<div key={i} className={`max-w-lg ${m.r==='me'?'self-end':'flex gap-2'}`}>
        {m.r==='ai'&&<span className="grid place-items-center size-8 shrink-0 rounded-full bg-sky-100 text-sky-600"><Sparkles size={16}/></span>}
        <div><p className={`rounded-3xl px-5 py-3 text-sm ${m.r==='me'?'bg-sky-500 text-white':'bg-sky-50'}`}>{m.t}</p>
          {m.src&&<p className="mt-1 ml-2 text-[11px] text-ink-soft">{badge[m.src]}</p>}
          {m.sql&&<details className="mt-1 ml-2 text-xs text-ink-soft"><summary className="cursor-pointer font-semibold">Show how I found this</summary>
            <pre className="mt-1 whitespace-pre-wrap rounded-2xl bg-sky-50 p-3">{m.sql}</pre></details>}</div></div>))}
      {busy&&<div className="flex gap-1.5 ml-10" aria-label="Thinking">{[0,1,2].map(i=><span key={i} className="size-2 rounded-full bg-sky-400 animate-pulse" style={{animationDelay:`${i*150}ms`}}/>)}</div>}
      <div ref={end}/></div>
    <div className="flex flex-wrap gap-2">{chips.map(s=><button key={s} onClick={()=>send(s)} disabled={busy} className="rounded-full bg-sky-100 hover:bg-sky-200 disabled:opacity-50 px-4 py-1.5 text-xs font-semibold">{s}</button>)}</div>
    <form onSubmit={e=>{e.preventDefault();send(q)}} className="flex gap-2 rounded-full bg-white p-2 pl-5 shadow-sm">
      <input value={q} onChange={e=>setQ(e.target.value)} maxLength={300} placeholder="Ask about your business" className="flex-1 outline-none text-sm bg-transparent"/>
      <button disabled={busy||!q.trim()} aria-label="Send" className="grid place-items-center size-10 rounded-full bg-sky-500 disabled:bg-sky-200 text-white"><Send size={16}/></button></form></div>)
}
