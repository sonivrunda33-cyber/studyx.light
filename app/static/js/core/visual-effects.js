const loader=document.querySelector('#appLoader');
const cursor=document.querySelector('#cursorGlow');
let activeGlass=null;
let cursorFrame=0;
let pointer={x:0,y:0};

function showLoader(){
  if(!loader)return;
  loader.classList.remove('is-hidden');
  loader.setAttribute('aria-hidden','false');
}

function hideLoader(){
  if(!loader)return;
  loader.classList.add('is-hidden');
  loader.setAttribute('aria-hidden','true');
}

function finishInitialLoad(){window.setTimeout(hideLoader,420)}
if(document.readyState==='complete')finishInitialLoad();
else window.addEventListener('load',finishInitialLoad,{once:true});
window.addEventListener('pageshow',event=>{if(event.persisted)hideLoader()});

document.addEventListener('click',event=>{
  const link=event.target.closest('a[href]');
  if(!link||event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
  if(link.target==='_blank'||link.hasAttribute('download'))return;
  const destination=new URL(link.href,location.href);
  if(destination.origin===location.origin&&destination.pathname!==location.pathname)showLoader();
});
document.addEventListener('submit',event=>{
  if(event.target.matches('[data-page-transition]'))showLoader();
});

if(cursor&&!matchMedia('(hover: none), (pointer: coarse), (prefers-reduced-motion: reduce)').matches){
  document.addEventListener('pointermove',event=>{
    pointer={x:event.clientX,y:event.clientY};
    const panel=event.target.closest?.('.glass-panel');
    if(activeGlass&&activeGlass!==panel)activeGlass.classList.remove('has-pointer');
    activeGlass=panel||null;
    if(activeGlass){
      const bounds=activeGlass.getBoundingClientRect();
      activeGlass.style.setProperty('--glass-x',`${event.clientX-bounds.left}px`);
      activeGlass.style.setProperty('--glass-y',`${event.clientY-bounds.top}px`);
      activeGlass.classList.add('has-pointer');
    }
    if(!cursorFrame)cursorFrame=requestAnimationFrame(()=>{
      cursor.style.left=`${pointer.x}px`;
      cursor.style.top=`${pointer.y}px`;
      cursor.classList.add('is-active');
      cursorFrame=0;
    });
    cursor.classList.toggle('is-hovering',Boolean(event.target.closest?.('a,button,input,select,textarea,[role="button"]')));
  },{passive:true});
  document.addEventListener('pointerleave',()=>{
    cursor.classList.remove('is-active','is-hovering');
    activeGlass?.classList.remove('has-pointer');
    activeGlass=null;
  });
  document.addEventListener('pointerdown',()=>cursor.classList.add('is-pressed'));
  document.addEventListener('pointerup',()=>cursor.classList.remove('is-pressed'));
}
