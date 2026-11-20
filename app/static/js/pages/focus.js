import {get,post,track} from '../core/api.js';
import {toast,emptyState} from '../core/ui.js';
import {minutesLabel,escapeHtml,dateLabel} from '../core/utils.js';

let planMinutes=25,remaining=1500,running=false,endAt=0,startAt=null,segmentStartedAt=0,elapsedSeconds=0,ticker=null;
export async function init(){
  const [tasks,analytics]=await Promise.all([get('/tasks'),get('/analytics')]);
  const subjects=[...new Set(tasks.map(task=>task.subject).filter(Boolean))];document.querySelector('#focusSubject').innerHTML=['Independent study',...subjects].map(subject=>`<option>${escapeHtml(subject)}</option>`).join('');
  updateStats(analytics);renderHistory(analytics.sessions.recent);
  document.querySelector('#timerModes')?.addEventListener('click',selectMode);
  document.querySelector('#timerStart')?.addEventListener('click',startPause);
  document.querySelector('#timerStop')?.addEventListener('click',()=>finish(false));
  document.querySelector('#timerReset')?.addEventListener('click',reset);
  display();
}
function selectMode(event){const button=event.target.closest('[data-minutes]');if(!button||running)return;document.querySelectorAll('#timerModes button').forEach(node=>node.classList.toggle('active',node===button));planMinutes=Number(button.dataset.minutes);remaining=planMinutes*60;startAt=null;segmentStartedAt=0;elapsedSeconds=0;display();document.querySelector('#timerLabel').textContent='READY WHEN YOU ARE'}
function startPause(){
  if(!running){running=true;if(!startAt)startAt=new Date().toISOString();segmentStartedAt=Date.now();endAt=segmentStartedAt+remaining*1000;ticker=setInterval(tick,250);document.querySelector('#timerStart').innerHTML='<span>Ⅱ</span> Pause';document.querySelector('#timerStop').disabled=false;document.querySelector('#timerLabel').textContent='ONE THING AT A TIME';document.querySelector('#timerRing').classList.add('running');track('focus_started',{planned_minutes:planMinutes})}
  else{running=false;const now=Date.now();remaining=Math.max(0,Math.ceil((endAt-now)/1000));elapsedSeconds+=Math.max(0,Math.floor((now-segmentStartedAt)/1000));segmentStartedAt=0;clearInterval(ticker);document.querySelector('#timerStart').innerHTML='<span>▶</span> Resume';document.querySelector('#timerLabel').textContent='PAUSED · READY WHEN YOU ARE';document.querySelector('#timerRing').classList.remove('running');display()}
}
function tick(){remaining=Math.max(0,Math.ceil((endAt-Date.now())/1000));display();if(remaining<=0)finish(true)}
async function finish(completed){
  if(!startAt){toast('Start a focus block first.','error');return}
  if(running&&segmentStartedAt){elapsedSeconds+=Math.max(0,Math.floor((Date.now()-segmentStartedAt)/1000))}const elapsed=elapsedSeconds;running=false;segmentStartedAt=0;clearInterval(ticker);
  try{await post('/sessions',{subject:document.querySelector('#focusSubject').value,planned_minutes:planMinutes,actual_minutes:Math.min(600,Math.round(elapsed/60)),completed,started_at:startAt,source:'pomodoro'});await track(completed?'focus_completed':'focus_finished_early',{planned_minutes:planMinutes,actual_seconds:elapsed});toast(completed?'Focus block complete — nice work.':'Your session was saved.');document.querySelector('#timerLabel').textContent=completed?'BLOCK COMPLETE':'SESSION SAVED';document.querySelector('#timerRing').classList.remove('running');document.querySelector('#timerStart').innerHTML='<span>▶</span> Start again';document.querySelector('#timerStop').disabled=true;startAt=null;const data=await get('/analytics');updateStats(data);renderHistory(data.sessions.recent)}catch(error){toast(error.message,'error')}
}
function reset(){running=false;clearInterval(ticker);remaining=planMinutes*60;startAt=null;segmentStartedAt=0;elapsedSeconds=0;document.querySelector('#timerStart').innerHTML='<span>▶</span> Start focus';document.querySelector('#timerStop').disabled=true;document.querySelector('#timerRing').classList.remove('running');document.querySelector('#timerLabel').textContent='READY WHEN YOU ARE';display()}
function display(){const mins=Math.floor(remaining/60),secs=remaining%60;document.querySelector('#timerDisplay').textContent=`${String(mins).padStart(2,'0')}:${String(secs).padStart(2,'0')}`;const ring=document.querySelector('#timerRing');if(ring)ring.style.setProperty('--timer-progress',`${Math.max(0,Math.min(100,(1-remaining/(planMinutes*60))*100))}%`)}
function updateStats(data){document.querySelector('#focusTotalSessions').textContent=data.sessions.total;document.querySelector('#focusTotalMinutes').textContent=minutesLabel(data.sessions.minutes_total);document.querySelector('#focusTodayMinutes').textContent=minutesLabel(data.sessions.minutes_today)}
function renderHistory(sessions){const holder=document.querySelector('#focusHistory');holder.innerHTML=sessions.length?sessions.map(session=>`<div class="history-row"><span class="history-icon">✳</span><div class="history-copy"><strong>${escapeHtml(session.subject)}</strong><small>${dateLabel(session.started_at,{month:'short',day:'numeric'})} · ${session.completed?'Completed':'Paused session'}</small></div><span class="history-minutes">${session.actual_minutes} min</span></div>`).join(''):emptyState('Your first session is waiting','Start a focus block and it will show up here.','◷')}
