import {get,post,remove,track} from '../core/api.js';
import {toast,openModal,closeModal,emptyState} from '../core/ui.js';
import {escapeHtml,dateLabel,colorFor} from '../core/utils.js';
import {courseCard} from '../core/renderers.js';

export async function init(){await Promise.all([renderExams(),renderCourses()]);
  document.querySelector('#addExamButton')?.addEventListener('click',()=>openModal('examModal'));
  document.querySelector('#examForm')?.addEventListener('submit',saveExam);
  document.querySelector('#examGrid')?.addEventListener('click',deleteExam);
  setInterval(renderCountdowns,60000);
}
async function renderExams(){
  const [exams,tasks]=await Promise.all([get('/exams'),get('/tasks')]);const grid=document.querySelector('#examGrid');
  const upcoming=exams.filter(exam=>new Date(exam.exam_at)>=new Date()).sort((a,b)=>a.exam_at.localeCompare(b.exam_at));
  document.querySelector('#examSummary').textContent=exams.length?`${upcoming.length} upcoming · ${tasks.filter(task=>task.status==='todo').length} open study tasks`:'';
  grid.innerHTML=exams.length?exams.map(exam=>{const days=Math.ceil((new Date(exam.exam_at)-new Date())/86400000);return `<article class="exam-card glass-panel ${escapeHtml(exam.color||colorFor(exam.subject))}"><div class="exam-subject"><i class="subject-dot ${colorFor(exam.subject)}"></i>${escapeHtml(exam.subject)}</div><h3>${escapeHtml(exam.title)}</h3><div class="exam-location">${escapeHtml(exam.location||'Location not added')}</div><div class="exam-count"><strong>${days<0?'Past':days===0?'Today':days}</strong><span>${days>0?'days to go':''}</span></div><div class="exam-date-row"><span>${dateLabel(exam.exam_at,{weekday:'short',month:'short',day:'numeric'})} · ${new Date(exam.exam_at).toLocaleTimeString(undefined,{hour:'numeric',minute:'2-digit'})}</span><button data-delete-exam="${exam.id}" title="Remove exam">Remove</button></div></article>`}).join(''):emptyState('No exams added yet','Add an exam date to keep it in sight.','✳');
}
async function renderCourses(){const courses=await get('/courses');document.querySelector('#courseList').innerHTML=courses.map(courseCard).join('')}
async function saveExam(event){event.preventDefault();const body=Object.fromEntries(new FormData(event.currentTarget).entries());try{await post('/exams',body);await track('exam_created');event.currentTarget.reset();closeModal('examModal');toast('Exam added');await renderExams()}catch(error){toast(error.message,'error')}}
async function deleteExam(event){const button=event.target.closest('[data-delete-exam]');if(!button)return;if(!confirm('Remove this exam from your planner?'))return;try{await remove(`/exams/${button.dataset.deleteExam}`);await track('exam_deleted');toast('Exam removed');await renderExams()}catch(error){toast(error.message,'error')}}
function renderCountdowns(){renderExams().catch(()=>{})}
