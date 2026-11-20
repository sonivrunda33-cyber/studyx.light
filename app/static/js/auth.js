const form=document.querySelector('.auth-form');
const toggle=document.querySelector('[data-password-toggle]');
toggle?.addEventListener('click',()=>{
  const input=form?.querySelector('input[name="password"]');
  if(!input)return;
  const reveal=input.type==='password';
  input.type=reveal?'text':'password';
  toggle.textContent=reveal?'Hide':'Show';
  toggle.setAttribute('aria-label',reveal?'Hide password':'Show password');
});
form?.addEventListener('submit',()=>{
  const button=form.querySelector('.auth-submit');
  if(button){button.disabled=true;button.querySelector('span').textContent='One moment…'}
});
