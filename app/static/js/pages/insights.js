import {get} from '../core/api.js';
import {renderChart,emptyState} from '../core/ui.js';
import {minutesLabel,escapeHtml,dateLabel} from '../core/utils.js';

export async function init(){const data=await get('/analytics');
  const week=data.sessions.by_day;const total=week.reduce((sum,day)=>sum+day.minutes,0);document.querySelector('#insightWeekMinutes').textContent=total;renderChart(document.querySelector('#insightsChart'),week);
  const percent=Math.round(data.tasks.completion_rate*100);document.querySelector('#taskProgressValue').textContent=`${percent}%`;document.querySelector('#taskProgressRing').style.setProperty('--progress',`${percent}%`);document.querySelector('#taskProgressCaption').textContent=`${data.tasks.completed} of ${data.tasks.total} tasks completed.`;
  const rows=data.sessions.recent;document.querySelector('#insightsSessions').innerHTML=rows.length?rows.map(row=>`<div class="data-row"><strong>${escapeHtml(row.subject)}</strong><span>${dateLabel(row.started_at,{month:'short',day:'numeric'})}</span><span>${row.actual_minutes} min</span></div>`).join(''):emptyState('No sessions yet','Your focus sessions will appear here.','◷');
  const subjects=Object.entries(data.sessions.by_subject||{}).sort((a,b)=>b[1]-a[1]);const max=Math.max(1,...subjects.map(item=>item[1]));document.querySelector('#subjectBreakdown').innerHTML=subjects.length?subjects.map(([subject,value])=>`<div class="subject-stat"><span class="subject-stat-name">${escapeHtml(subject)}</span><span class="subject-stat-value">${minutesLabel(value)}</span><div class="progress-track"><div class="progress-fill" style="width:${value/max*100}%"></div></div></div>`).join(''):emptyState('No study time recorded','Complete a focus session to see subjects here.','✳');
}
