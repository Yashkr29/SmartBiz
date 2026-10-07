import {useState} from 'react'
import {Mail,Lock,User} from 'lucide-react'
import {useAuth} from '../App.jsx'
import {errMsg} from '../api.js'

const Field=({icon:Icon,...p})=>(<label className="flex items-center gap-3 rounded-full bg-white shadow-[0_6px_20px_rgba(91,134,229,.18)] px-5 py-3.5">
  <Icon size={18} className="text-sky-500"/><input {...p} required className="flex-1 bg-transparent outline-none text-sm placeholder:text-ink-soft/70"/></label>)

function Art(){return(<svg viewBox="0 0 320 260" className="w-full max-w-md" role="img" aria-label="Laptop on a desk">
  <rect x="70" y="30" width="170" height="115" rx="8" fill="#fff" stroke="#1d2340" strokeWidth="9"/>
  <rect x="40" y="150" width="230" height="16" rx="5" fill="#fff" stroke="#1d2340" strokeWidth="5"/>
  <rect x="100" y="152" width="70" height="8" rx="3" fill="#7ea2ee"/>
  <rect x="20" y="110" width="34" height="38" rx="6" fill="#fff" stroke="#9db8f3" strokeWidth="5"/>
  <path d="M275 150c-20-30-5-60 0-80 8 25 25 50 0 80zM290 150c10-20 25-35 35-45-5 25-12 35-35 45z" fill="#5b86e5"/>
  <rect x="262" y="150" width="46" height="46" rx="10" fill="#fff" stroke="#1d2340" strokeWidth="4"/></svg>)}

export default function Login(){
  const {login,register}=useAuth(),[tab,setTab]=useState('login'),[f,setF]=useState({name:'',email:'',password:''})
  const set=k=>e=>setF({...f,[k]:e.target.value})
  const [err,setErr]=useState(''),[busy,setBusy]=useState(false)
  const submit=async e=>{e.preventDefault();setErr('');setBusy(true)
    try{tab==='login'?await login(f.email,f.password):await register(f.name,f.email,f.password)}
    catch(x){setErr(errMsg(x))}finally{setBusy(false)}}
  return(<div className="min-h-screen grid lg:grid-cols-2 bg-white overflow-hidden">
    <section className="flex flex-col px-8 sm:px-16 py-8">
      <div className="text-xl font-extrabold">Smart<span className="text-sky-600">Biz</span></div>
      <form onSubmit={submit} className="m-auto w-full max-w-sm space-y-5">
        <div className="flex gap-8 text-lg font-bold" role="tablist">
          {['login','signup'].map(t=>(<button type="button" key={t} role="tab" aria-selected={tab===t} onClick={()=>setTab(t)}
            className={`pb-1 border-b-2 ${tab===t?'border-sky-400':'border-transparent text-sky-200'}`}>{t==='login'?'Login':'Sign up'}</button>))}</div>
        {tab==='signup'&&<Field icon={User} placeholder="Business owner name" value={f.name} onChange={set('name')}/>}
        <Field icon={Mail} type="email" placeholder="Email address" value={f.email} onChange={set('email')}/>
        <Field icon={Lock} type="password" minLength={6} placeholder="Password (min 6 characters)" value={f.password} onChange={set('password')}/>
        <div className="flex items-center justify-between">
          <a href="#" className="text-xs text-ink-soft hover:underline">Forgot your password?</a>
          <button disabled={busy} className="disabled:opacity-60 rounded-full bg-sky-500 hover:bg-sky-600 text-white font-semibold px-10 py-2.5 shadow-lg shadow-sky-400/40">{tab==='login'?'Login':'Create account'}</button></div>
        {err&&<p role="alert" className="text-sm text-rose-600">{err}</p>}
      </form></section>
    <section className="relative hidden lg:grid place-items-center">
      {[['w-[900px] h-[900px] bg-sky-100/70'],['w-[700px] h-[700px] bg-sky-200/70'],['w-[500px] h-[500px] bg-sky-400/60']].map(([c])=>
        <div key={c} className={`absolute rounded-full left-1/2 top-1/2 -translate-y-1/2 -translate-x-1/4 ${c}`}/>)}
      <div className="relative"><Art/><p className="text-center font-bold mt-4">Orders, stock and payments, in one place.</p></div></section></div>)
}
