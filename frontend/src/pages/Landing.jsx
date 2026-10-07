import {Link} from 'react-router-dom'
import {ShoppingBag,Package,Wallet,LayoutDashboard,FileSpreadsheet,Sparkles} from 'lucide-react'

const features=[[ShoppingBag,'Order tracking','Move every order from New to Delivered and see where it is stuck.'],
[Package,'Automatic stock','Stock drops when an order is created and you see low items early.'],
[Wallet,'Payments','Advance, received and pending amounts for every order.'],
[LayoutDashboard,'Live dashboard','Sales, expenses and estimated profit on one screen.'],
[FileSpreadsheet,'Excel import','Bring in your old sheets and map the columns in a minute.'],
[Sparkles,'Ask in plain English','Ask who owes you the most and get the answer straight away.']]

function Preview(){return(<div className="mx-auto max-w-3xl rounded-[28px] bg-white/40 backdrop-blur-md p-3 shadow-2xl shadow-ink/20">
  <div className="rounded-2xl bg-white/85 p-4 grid grid-cols-[110px_1fr] gap-4 text-left">
    <div className="hidden sm:block space-y-2 text-xs font-semibold text-ink-soft">
      {['Overview','Orders','Customers','Inventory','Expenses'].map((t,i)=><p key={t} className={`rounded-full px-3 py-1.5 ${i===0?'bg-sky-100 text-ink':''}`}>{t}</p>)}</div>
    <div className="col-span-2 sm:col-span-1 space-y-3">
      <div className="grid grid-cols-3 gap-3">{[['Sales','₹1.54L'],['Active orders','3'],['Pending','₹54,500']].map(([l,v],i)=>(
        <div key={l} className={`rounded-xl p-3 ${i===0?'bg-ink text-white':'bg-sky-50'}`}><p className="text-[10px] opacity-70">{l}</p><p className="font-extrabold">{v}</p></div>))}</div>
      <svg viewBox="0 0 300 70" className="w-full h-16" aria-hidden="true"><path d="M0 55C40 50 60 20 100 35S170 60 210 25 270 15 300 30V70H0Z" fill="#e3ebff"/><path d="M0 55C40 50 60 20 100 35S170 60 210 25 270 15 300 30" fill="none" stroke="#5b86e5" strokeWidth="3"/></svg></div></div></div>)}

export default function Landing(){
  return(<div>
    <section className="text-center text-white px-5 pb-16" style={{background:'radial-gradient(ellipse at 15% 5%,rgba(255,255,255,.55),transparent 35%),radial-gradient(ellipse at 85% 25%,rgba(255,255,255,.4),transparent 30%),linear-gradient(180deg,#3d6fd1,#8fb0ee 75%,#f4f6fc)'}}>
      <nav className="max-w-6xl mx-auto flex items-center justify-between py-5">
        <span className="text-xl font-extrabold">SmartBiz</span>
        <div className="hidden md:flex gap-8 text-sm font-semibold"><a href="#features">Features</a><Link to="/login">Login</Link></div>
        <Link to="/login" className="rounded-full bg-white text-ink text-sm font-bold px-5 py-2">Get started</Link></nav>
      <h1 className="mt-16 text-4xl sm:text-6xl font-extrabold leading-tight max-w-3xl mx-auto">Run your whole shop from one screen.</h1>
      <p className="mt-5 max-w-xl mx-auto text-white/90">Customers, orders, stock, payments and expenses stay connected, so you always know what you are owed.</p>
      <Link to="/login" className="inline-block mt-8 mb-14 rounded-full bg-ink px-8 py-3 font-bold">Open your account</Link>
      <Preview/></section>
    <section id="features" className="max-w-5xl mx-auto px-5 py-20 text-center">
      <span className="rounded-full bg-white px-4 py-1 text-xs font-bold text-ink-soft shadow-sm">Features</span>
      <h2 className="mt-4 text-3xl sm:text-4xl font-extrabold">Everything your business needs to stay on track</h2>
      <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-10">{features.map(([Icon,t,d])=>(
        <div key={t} className="flex flex-col items-center"><span className="grid place-items-center size-11 rounded-full bg-sky-100 text-sky-600"><Icon size={20}/></span>
          <h3 className="mt-3 font-bold">{t}</h3><p className="mt-1 text-sm text-ink-soft max-w-60">{d}</p></div>))}</div></section></div>)
}
