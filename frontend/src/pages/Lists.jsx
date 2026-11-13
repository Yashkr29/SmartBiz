import {useState} from 'react'
import {Search,Plus,Trash2,Pencil,Upload,X} from 'lucide-react'
import {api,errMsg} from '../api.js'
import {useApi,Status,Banner,inr} from '../ui.jsx'
import {useAuth} from '../App.jsx'
import ImportCsv from './ImportCsv.jsx'

const isNum=t=>['num','money'].includes(t)

// col: k = API field, l = label, t = text|num|money|date, opt = optional in the form, ro = display only
function List({title,noun,path,cols,sample}){
  const {data,loading,error,reload}=useApi(path),{user}=useAuth()
  const [q,setQ]=useState(''),[panel,setPanel]=useState(null),[draft,setDraft]=useState({}),[editing,setEditing]=useState(null),[msg,setMsg]=useState(''),[busy,setBusy]=useState(false)
  if(!data)return <Status {...{loading,error,reload}}/>
  const fields=cols.filter(c=>!c.ro)
  const needle=q.trim().toLowerCase()
  const shown=needle?data.filter(r=>cols.some(c=>String(r[c.k]??'').toLowerCase().includes(needle))):data
  const run=async fn=>{setMsg('');setBusy(true);try{await fn();await reload()}catch(x){setMsg(errMsg(x))}finally{setBusy(false)}}
  const open=p=>{setMsg('');setPanel(panel===p?null:p);if(p!=='form'||panel==='form'){setEditing(null);setDraft({})}}
  const startEdit=r=>{setMsg('');setEditing(r.id);setPanel('form');setDraft(Object.fromEntries(fields.map(f=>[f.k,r[f.k]??''])))}
  const close=()=>{setPanel(null);setEditing(null);setDraft({})}
  const save=e=>{e.preventDefault()
    const body={};fields.forEach(f=>{const v=draft[f.k];if(v!==undefined&&v!=='')body[f.k]=isNum(f.t)?+v:v;else if(editing&&f.opt&&f.t!=='date')body[f.k]=''})
    run(async()=>{editing?await api.put(`${path}/${editing}`,body):await api.post(path,body);close()})}
  const cell=(r,c)=>c.t==='money'?inr(r[c.k]):r[c.k]
  const label=r=>r.name||r.title
  return(<div className="space-y-5"><div className="flex items-center justify-between gap-3 flex-wrap"><h1 className="text-2xl font-extrabold">{title}</h1>
    <div className="flex flex-wrap gap-2"><label className="flex items-center gap-2 rounded-full bg-white px-4 py-2"><Search size={16} className="text-sky-500"/>
      <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search" aria-label="Search" className="outline-none text-sm bg-transparent w-36"/></label>
      <button onClick={()=>open('import')} aria-expanded={panel==='import'} className="flex items-center gap-1 rounded-full bg-white text-sky-600 text-sm font-semibold px-5 py-2 hover:bg-sky-50"><Upload size={16}/>Import CSV</button>
      <button onClick={()=>open('form')} aria-expanded={panel==='form'} className="flex items-center gap-1 rounded-full bg-sky-500 text-white text-sm font-semibold px-5 py-2"><Plus size={16}/>Add</button></div></div>
    <Banner>{msg}</Banner>
    {panel==='import'&&<ImportCsv entity={path.slice(1)} title={title} cols={fields} sample={sample} onClose={close} onImported={reload}/>}
    {panel==='form'&&<form onSubmit={save} className="rounded-3xl bg-white/85 p-5 space-y-3">
      <div className="flex items-center justify-between"><h2 className="font-bold">{editing?`Edit ${noun}`:`New ${noun}`}</h2>
        <button type="button" onClick={close} aria-label="Close" className="text-ink-soft hover:text-ink"><X size={18}/></button></div>
      <div className="grid sm:grid-cols-3 gap-3">
      {fields.map(f=><input key={f.k} required={!f.opt} aria-label={f.l} title={f.l} placeholder={f.l+(f.opt?' (optional)':'')}
        type={f.t==='date'?'date':isNum(f.t)?'number':'text'} min={isNum(f.t)?0:undefined} step={f.t==='money'?'0.01':undefined}
        value={draft[f.k]??''} onChange={e=>setDraft({...draft,[f.k]:e.target.value})} className="rounded-full bg-sky-50 px-4 py-2.5 text-sm outline-none"/>)}
      <button disabled={busy} className="rounded-full bg-ink text-white text-sm font-semibold py-2.5 disabled:opacity-60">{editing?'Save changes':`Save ${noun}`}</button></div></form>}
    <div className="rounded-3xl bg-white/85 shadow-sm shadow-sky-200/60 p-2 overflow-x-auto"><table className="w-full text-sm">
      <thead className="text-left text-ink-soft"><tr>{cols.map(c=><th key={c.k} className="p-3 font-semibold">{c.l}</th>)}<th className="w-16"/></tr></thead>
      <tbody>{shown.map(r=><tr key={r.id} className={`hover:bg-sky-50 ${editing===r.id?'bg-sky-50':''}`}>{cols.map(c=><td key={c.k} className="p-3">{cell(r,c)}</td>)}
        <td className="p-3"><div className="flex gap-3 justify-end">
          <button aria-label={`Edit ${label(r)}`} onClick={()=>startEdit(r)} className="text-ink-soft hover:text-sky-600"><Pencil size={16}/></button>
          {user.role==='admin'&&<button aria-label={`Delete ${label(r)}`} disabled={busy} onClick={()=>confirm(`Delete ${label(r)}?`)&&run(()=>api.delete(`${path}/${r.id}`))} className="text-ink-soft hover:text-rose-600"><Trash2 size={16}/></button>}</div></td></tr>)}
      {!shown.length&&<tr><td className="p-6 text-ink-soft" colSpan={cols.length+1}>{data.length?'Nothing matches your search.':`No ${title.toLowerCase()} yet. Use Add, or Import CSV to bring in an existing sheet.`}</td></tr>}</tbody></table></div>
    {data.length>0&&<p className="text-xs text-ink-soft px-2">{shown.length} of {data.length} {title.toLowerCase()}</p>}</div>)
}
export const Customers=()=><List title="Customers" noun="customer" path="/customers" sample={['Asha Traders','9822011234','Pune']}
  cols={[{k:'name',l:'Name'},{k:'phone',l:'Phone',opt:1},{k:'city',l:'City',opt:1},{k:'due',l:'Amount due',t:'money',ro:1}]}/>
export const Products=()=><List title="Inventory" noun="product" path="/products" sample={['Teak Study Table','TST-01','10','3','12500']}
  cols={[{k:'name',l:'Product'},{k:'sku',l:'SKU'},{k:'stock',l:'In stock',t:'num'},{k:'reorder_level',l:'Reorder level',t:'num'},{k:'price',l:'Price',t:'money'}]}/>
export const Suppliers=()=><List title="Suppliers" noun="supplier" path="/suppliers" sample={['Wood Depot','9890155621','Teak wood']}
  cols={[{k:'name',l:'Name'},{k:'phone',l:'Phone',opt:1},{k:'item',l:'Supplies',opt:1}]}/>
export const Expenses=()=><List title="Expenses" noun="expense" path="/expenses" sample={['Shop rent','Rent','15000','2026-11-01']}
  cols={[{k:'title',l:'Expense'},{k:'category',l:'Category',opt:1},{k:'amount',l:'Amount',t:'money'},{k:'date',l:'Date',t:'date',opt:1}]}/>
