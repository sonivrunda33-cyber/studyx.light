import {get} from '../core/api.js';
import {renderChart,emptyState} from '../core/ui.js';
import {dateLabel,timeLabel,isoDay,colorFor,minutesLabel,escapeHtml} from '../core/utils.js';

export async function init(){
  const [tasks,exams,data,studyx]=await Promise.all([get('/tasks'),get('/exams'),get('/analytics'),get('/studyx/dashboard')]);
  const name=studyx.profile.full_name||document.body.dataset.accountName||'Student';const first=name.split(/\s+/)[0];
  const hour=new Date().getHours();const salutation=hour<12?'Good morning':hour<17?'Good afternoon':'Good evening';
  document.querySelector('#welcomeTitle').innerHTML=`${salutation}, ${escapeHtml(first)}.<br><span>One step at a time.</span>`;
  document.querySelector('#todayLabel').textContent=new Date().toLocaleDateString(undefined,{weekday:'long',month:'long',day:'numeric'}).toUpperCase();
  document.querySelector('#welcomeCopy').textContent='Give today a little structure. You have got this.';
  document.querySelector('#statCompleted').textContent=`${data.tasks.completed}/${data.tasks.total}`;
  document.querySelector('#statCompletionRate').textContent=`${Math.round(data.tasks.completion_rate*100)}%`;
  const weekMinutes=data.sessions.by_day.reduce((sum,day)=>sum+day.minutes,0);
  document.querySelector('#statWeekHours').textContent=minutesLabel(weekMinutes);
  document.querySelector('#weekMinutes').textContent=weekMinutes;
  document.querySelector('#statSessions').textContent=data.sessions.total;
  document.querySelector('#statQuizAverage').textContent=studyx.quizzes.average_score===null?'—':String(studyx.quizzes.average_score)+'%';
  document.querySelector('#statQuizCaption').textContent=studyx.quizzes.attempt_count?String(studyx.quizzes.attempt_count)+' saved attempt'+(studyx.quizzes.attempt_count===1?'':'s'):'No quiz attempts saved';
  document.querySelector('#statRoadmapProgress').textContent=studyx.roadmaps.completion_percent===null?'—':String(studyx.roadmaps.completion_percent)+'%';
  document.querySelector('#statRoadmapCaption').textContent=studyx.roadmaps.count?String(studyx.roadmaps.completed_tasks)+'/'+String(studyx.roadmaps.total_tasks)+' roadmap tasks done':'No roadmap saved';
  document.querySelector('#statLearningProgress').textContent=studyx.progress.average_percent===null?'—':String(studyx.progress.average_percent)+'%';
  document.querySelector('#statLearningCaption').textContent=studyx.progress.average_percent===null?'No roadmap progress yet':'Across '+studyx.progress.subjects+' subject(s)';
  const futureExams=exams.filter(exam=>new Date(exam.exam_at)>=new Date()).sort((a,b)=>a.exam_at.localeCompare(b.exam_at));
  if(futureExams[0]){const days=Math.ceil((new Date(futureExams[0].exam_at)-new Date())/86400000);document.querySelector('#statExamDays').textContent=days===0?'Today':`${days} days`;document.querySelector('#statExamName').textContent=futureExams[0].title}else{document.querySelector('#statExamDays').textContent='—'}
  renderChart(document.querySelector('#weeklyChart'),data.sessions.by_day);
  const upcoming=tasks.filter(task=>task.status==='todo').sort((a,b)=>(a.due_at||'9999').localeCompare(b.due_at||'9999')).slice(0,4);
  document.querySelector('#dashboardAgenda').innerHTML=upcoming.length?upcoming.map(task=>`<div class="agenda-item"><span class="agenda-time">${task.due_at?timeLabel(task.due_at):'Any time'}</span><div class="agenda-item-main"><i class="subject-dot ${colorFor(task.subject)}"></i><div><h4>${escapeHtml(task.title)}</h4><p>${escapeHtml(task.subject)} · ${task.duration_minutes} min</p></div></div><span class="agenda-tag">${escapeHtml(task.priority)}</span></div>`).join(''):emptyState('A clear day','Add a task when you are ready to plan.');
  renderMiniWeek(tasks);
}
function renderMiniWeek(tasks){
  const holder=document.querySelector('#miniWeek');if(!holder)return;const today=new Date();const monday=new Date(today);monday.setDate(today.getDate()-((today.getDay()+6)%7));
  holder.innerHTML=Array.from({length:7},(_,i)=>{const day=new Date(monday);day.setDate(monday.getDate()+i);const dayKey=isoDay(day);const has=tasks.some(task=>task.due_at?.slice(0,10)===dayKey);return `<div class="mini-day ${dayKey===isoDay(today)?'today':''} ${has?'has-task':''}"><span>${day.toLocaleDateString(undefined,{weekday:'short'})}</span><b>${day.getDate()}</b></div>`}).join('');
}
