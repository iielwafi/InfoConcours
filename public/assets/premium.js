(()=>{
  const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const toast=(message)=>{
    let node=document.getElementById('icToast');
    if(!node){node=document.createElement('div');node.id='icToast';node.className='ic-toast';node.setAttribute('role','status');node.setAttribute('aria-live','polite');document.body.append(node)}
    node.textContent=message;node.classList.add('visible');window.clearTimeout(node.dismissTimer);node.dismissTimer=window.setTimeout(()=>node.classList.remove('visible'),2200);
  };

  document.querySelectorAll('.code-example code').forEach((code)=>{
    const source=code.textContent;
    const escape=(value)=>value.replace(/[&<>"']/g,(char)=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const pattern=/(#.*|--.*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:def|return|if|else|elif|for|while|in|and|or|not|True|False|None|class|import|from|as|try|except|with|lambda|pass|break|continue|CREATE|TABLE|PRIMARY|KEY|NOT|NULL|INSERT|INTO|VALUES|SELECT|FROM|WHERE|ORDER|BY|JOIN|ON|GROUP|COUNT|UPDATE|SET|DELETE|BEGIN|COMMIT|ROLLBACK)\b|\b\d+(?:\.\d+)?\b)/g;
    let html='',last=0,match;
    while((match=pattern.exec(source))!==null){html+=escape(source.slice(last,match.index));const value=match[0],kind=/^(#|--)/.test(value)?'comment':/^["']/.test(value)?'string':/^\d/.test(value)?'number':'keyword';html+=`<span class="syntax-${kind}">${escape(value)}</span>`;last=pattern.lastIndex}
    html+=escape(source.slice(last));code.innerHTML=html;
    const pre=code.closest('pre');if(!pre)return;
    const copyLabel=document.documentElement.lang==='ar'?'نسخ الرمز':'Copier le code';
    const button=document.createElement('button');button.type='button';button.className='copy-code';button.textContent=copyLabel;button.setAttribute('aria-label',copyLabel);
    button.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(source)}catch(error){const temporary=document.createElement('textarea');temporary.value=source;temporary.style.position='fixed';temporary.style.opacity='0';document.body.append(temporary);temporary.select();document.execCommand('copy');temporary.remove()}button.textContent=document.documentElement.lang==='ar'?'تنسخ ✓':'Copié ✓';toast(document.documentElement.lang==='ar'?'تم نسخ الرمز.':'Code copié dans le presse-papiers.');window.setTimeout(()=>button.textContent=copyLabel,1800)});
    pre.append(button);
  });

  const progress=document.getElementById('readingProgress');
  if(progress){
    const update=()=>{const root=document.documentElement,scrollable=root.scrollHeight-root.clientHeight,value=scrollable>0?Math.min(100,Math.max(0,root.scrollTop/scrollable*100)):0;progress.style.width=`${value}%`;const label=document.getElementById('readingPercent');if(label)label.textContent=`${Math.round(value)}%`};
    window.addEventListener('scroll',update,{passive:true});window.addEventListener('resize',update);update();
    if(!reducedMotion&&'IntersectionObserver'in window){const sections=[...document.querySelectorAll('.lesson-content>section[id]')],links=[...document.querySelectorAll('.lesson-toc a')];const observer=new IntersectionObserver((entries)=>{for(const entry of entries)if(entry.isIntersecting){for(const link of links)link.classList.toggle('is-current',link.hash===`#${entry.target.id}`)}},{rootMargin:'-20% 0px -68% 0px'});sections.forEach(section=>observer.observe(section))}
  }

  document.querySelectorAll('.nav-more').forEach((details)=>{
    document.addEventListener('click',(event)=>{if(details.open&&!details.contains(event.target))details.open=false});
    details.querySelectorAll('a').forEach((link)=>link.addEventListener('click',()=>details.open=false));
    details.addEventListener('keydown',(event)=>{if(event.key==='Escape'){details.open=false;details.querySelector('summary').focus()}});
  });

  const clock=document.getElementById('examClock');
  if(clock){clock.setAttribute('role','timer');clock.setAttribute('aria-live','off');const update=()=>{const [h,m]=clock.textContent.split(':').map(Number);const urgent=h*3600+m*60<600;clock.closest('.timer')?.classList.toggle('is-urgent',urgent)};update();new MutationObserver(update).observe(clock,{childList:true,characterData:true,subtree:true})}
  document.querySelectorAll('.flash').forEach((flash)=>{if(flash.classList.contains('success'))window.setTimeout(()=>{flash.classList.add('is-dismissed');window.setTimeout(()=>flash.remove(),250)},5500)});
})();
