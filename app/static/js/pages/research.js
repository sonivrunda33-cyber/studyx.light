import {get,post} from '../core/api.js';
import {toast,emptyState} from '../core/ui.js';
import {escapeHtml} from '../core/utils.js';

const susPrompts=[
  'I would like to use this planner frequently.',
  'I found the planner more complicated than it needed to be.',
  'I thought the planner was easy to use.',
  'I think I would need help from someone technical to use this planner.',
  'I found the planner’s features fit together well.',
  'I thought there was too much inconsistency in the planner.',
  'I imagine most students would learn to use this planner quickly.',
  'I found the planner awkward to use.',
  'I felt confident using the planner.',
  'I needed to learn a lot before I could get started.'
];

export async function init(){
  renderSusQuestions();await refreshSnapshot();
  document.querySelector('#surveyForm')?.addEventListener('submit',submitSurvey);
  document.querySelector('#usabilityForm')?.addEventListener('submit',submitUsability);
}
function renderSusQuestions(){
  const holder=document.querySelector('#susQuestions');
  holder.innerHTML=susPrompts.map((prompt,index)=>`<div class="sus-question"><p><span class="question-number">${String(index+1).padStart(2,'0')}</span>${prompt}</p><div class="likert-inline" role="radiogroup" aria-label="Usability statement ${index+1}">${[1,2,3,4,5].map(value=>`<label><input type="radio" name="sus_${index+1}" value="${value}" required><span>${value}</span></label>`).join('')}</div></div>`).join('');
}
async function submitSurvey(event){
  event.preventDefault();const form=event.currentTarget;const formData=new FormData(form);const body={
    primary_challenge:formData.get('primary_challenge'),planning_method:formData.get('planning_method'),
    planning_difficulty:Number(formData.get('planning_difficulty')),satisfaction:Number(formData.get('satisfaction')),
    missed_tasks:Number(formData.get('missed_tasks')),current_method_hours:Number(formData.get('current_method_hours')),
    feedback:formData.get('feedback'),consent_confirmed:Number(formData.get('consent_confirmed'))
  };
  try{await post('/feedback',body);form.reset();toast('Survey response saved');await refreshSnapshot()}
  catch(error){toast(error.message,'error')}
}
async function submitUsability(event){
  event.preventDefault();const formData=new FormData(event.currentTarget);const data=Object.fromEntries(formData.entries());
  for(const key of ['baseline_minutes','prototype_minutes','baseline_errors','prototype_errors','baseline_success','prototype_success','satisfaction'])data[key]=Number(data[key]);
  data.sus_answers=Array.from({length:10},(_,i)=>Number(formData.get(`sus_${i+1}`)));
  try{const result=await post('/usability-tests',data);event.currentTarget.reset();toast(`Test result saved · SUS ${result.sus_score}`);await refreshSnapshot()}
  catch(error){toast(error.message,'error')}
}
async function refreshSnapshot(){
  const data=await get('/analytics');const feedback=data.feedback;const us=data.usability;
  document.querySelector('#researchSurveyN').textContent=feedback.n;
  document.querySelector('#researchSus').textContent=us.mean_sus==null?'—':us.mean_sus.toFixed(1);
  document.querySelector('#surveyCount').textContent=`${feedback.n} / 30 responses`;
  document.querySelector('#researchPairs').textContent=us.n;
  if(us.n){
    const rows=[['Participants',us.n],['Mean current-method time',us.mean_baseline==null?'—':`${us.mean_baseline.toFixed(1)} min`],['Mean prototype time',us.mean_prototype==null?'—':`${us.mean_prototype.toFixed(1)} min`],['Mean time saved',us.mean_improvement==null?'—':`${us.mean_improvement.toFixed(1)} min`],['Current task success',us.success_baseline==null?'—':`${Math.round(us.success_baseline*100)}%`],['Prototype task success',us.success_prototype==null?'—':`${Math.round(us.success_prototype*100)}%`],['Mean errors reduced',us.mean_error_reduction==null?'—':us.mean_error_reduction.toFixed(2)],['Test used',us.test||'Descriptive only'],['p-value',us.p_value==null?'Not calculated':us.p_value.toFixed(4)]];
    if(us.effect_size!=null)rows.push([us.effect_name||'Effect size',us.effect_size.toFixed(3)]);
    if(us.ci95)rows.push([`95% CI · ${us.ci_method||'time saved'}`,`${us.ci95[0].toFixed(1)} to ${us.ci95[1].toFixed(1)} min`]);
    document.querySelector('#pairedSummary').className='analysis-result';document.querySelector('#pairedSummary').innerHTML=rows.map(([label,value])=>`<div class="analysis-result-row"><span>${label}</span><strong>${escapeHtml(value)}</strong></div>`).join('');
  }else{document.querySelector('#pairedSummary').className='empty-report';document.querySelector('#pairedSummary').textContent='Save paired measurements to calculate the comparison.'}
  const challenges=Object.entries(feedback.primary_challenges||{}).sort((a,b)=>b[1]-a[1]);
  document.querySelector('#challengeSummary').innerHTML=challenges.length?challenges.slice(0,5).map(([name,count])=>`<div class="analysis-result-row"><span>${escapeHtml(name)}</span><strong>${count}</strong></div>`).join(''):'No survey responses yet.';
  const surveyStats=document.querySelector('#surveyStats');
  surveyStats.className=feedback.n?'analysis-result':'empty-report';
  surveyStats.innerHTML=feedback.n?[
    ['Mean planning difficulty',feedback.mean_difficulty?.toFixed(2)??'—'],
    ['Mean current-method satisfaction',feedback.mean_satisfaction?.toFixed(2)??'—'],
    ['Spearman difficulty ↔ satisfaction',feedback.difficulty_satisfaction_rho==null?'Need more varied responses':feedback.difficulty_satisfaction_rho.toFixed(2)]
  ].map(([label,value])=>`<div class="analysis-result-row"><span>${label}</span><strong>${escapeHtml(value)}</strong></div>`).join(''):'Save responses to calculate averages.';
  const usage=document.querySelector('#usageSummary');
  usage.className=data.events.total?'analysis-result':'empty-report';
  usage.innerHTML=data.events.total?[
    ['Recorded interactions',data.events.total],
    ['Timed interactions',data.events.timed],
    ['Recorded focus minutes',data.sessions.minutes_total]
  ].map(([label,value])=>`<div class="analysis-result-row"><span>${label}</span><strong>${escapeHtml(value)}</strong></div>`).join(''):'No interaction events recorded yet.';
}
