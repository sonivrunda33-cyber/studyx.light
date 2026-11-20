import {toast} from '../core/ui.js';
import {setProfile} from '../core/utils.js';
import {get,patch} from '../core/api.js';

export async function init(){
  const form=document.querySelector('#profileForm');
  const reminder=document.querySelector('#reminderToggle');
  let profile;
  try{
    profile=await get('/studyx/profile');
    document.querySelector('#settingName').value=profile.full_name||'';
    document.querySelector('#settingCourse').value=profile.course_name||'';
    document.querySelector('#settingImageUrl').value=profile.profile_image_url||'';
    const preferences=profile.preferences||{};
    document.querySelector('#settingGoal').value=preferences.weekly_goal_hours??'';
    reminder.checked=Boolean(preferences.reminders_enabled);
  }catch(error){toast(error.message,'error');return}
  form?.addEventListener('submit',async event=>{
    event.preventDefault();
    const preferences={...(profile.preferences||{}),weekly_goal_hours:Number(form.elements.goal.value),reminders_enabled:reminder.checked};
    try{
      profile=await patch('/studyx/profile',{
        full_name:form.elements.name.value.trim(),
        course_name:form.elements.course.value.trim(),
        profile_image_url:form.elements.profile_image_url.value.trim(),
        preferences,
      });
      document.body.dataset.accountName=profile.full_name;
      setProfile(profile.full_name);
      toast('Profile and preferences saved to your account');
    }catch(error){toast(error.message,'error')}
  });
}
