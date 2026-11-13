(()=>{
  const palette={line:'#6757e8',fill:'rgba(103,87,232,.16)',grid:'#dfe2eb',text:'#747b90'};
  function prepare(canvas,draw){
    if(!canvas)return;
    const ctx=canvas.getContext('2d');let points=[];
    function render(){const dark=document.body.classList.contains('dark');palette.line=dark?'#9b94ff':'#6757e8';palette.fill=dark?'rgba(155,148,255,.2)':'rgba(103,87,232,.16)';palette.grid=dark?'#39445c':'#dfe2eb';palette.text=dark?'#a8b3c9':'#747b90';const box=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1,w=Math.max(280,box.width),h=Math.max(240,box.height);canvas.width=w*dpr;canvas.height=h*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);points=draw(ctx,w,h)}
    canvas.addEventListener('pointermove',event=>{const rect=canvas.getBoundingClientRect(),x=event.clientX-rect.left,y=event.clientY-rect.top;let nearest=null,dist=Infinity;for(const p of points){const d=Math.hypot(p.x-x,p.y-y);if(d<dist){nearest=p;dist=d}}canvas.title=nearest&&dist<24?nearest.label:''});
    new ResizeObserver(render).observe(canvas);new MutationObserver(render).observe(document.body,{attributes:true,attributeFilter:['class']});render();
  }
  function radar(canvas,labels,values){
    prepare(canvas,(c,w,h)=>{const cx=w/2,cy=h/2,r=Math.min(w,h)*.31,n=labels.length,pts=[];if(!n)return pts;c.font='11px Arial';c.textAlign='center';c.textBaseline='middle';
      for(let ring=1;ring<=5;ring++){c.beginPath();for(let i=0;i<n;i++){const a=-Math.PI/2+i*2*Math.PI/n,x=cx+Math.cos(a)*r*ring/5,y=cy+Math.sin(a)*r*ring/5;i?c.lineTo(x,y):c.moveTo(x,y)}c.closePath();c.strokeStyle=palette.grid;c.stroke()}
      for(let i=0;i<n;i++){const a=-Math.PI/2+i*2*Math.PI/n,x=cx+Math.cos(a)*r,y=cy+Math.sin(a)*r;c.beginPath();c.moveTo(cx,cy);c.lineTo(x,y);c.strokeStyle=palette.grid;c.stroke();c.fillStyle=palette.text;c.fillText(labels[i],cx+Math.cos(a)*(r+23),cy+Math.sin(a)*(r+23))}
      c.beginPath();for(let i=0;i<n;i++){const a=-Math.PI/2+i*2*Math.PI/n,v=Math.max(0,Math.min(100,values[i]||0))/100,x=cx+Math.cos(a)*r*v,y=cy+Math.sin(a)*r*v;i?c.lineTo(x,y):c.moveTo(x,y);pts.push({x,y,label:`${labels[i]} : ${values[i]} %`})}c.closePath();c.fillStyle=palette.fill;c.fill();c.strokeStyle=palette.line;c.lineWidth=2;c.stroke();return pts});
  }
  function bars(canvas,labels,values){
    prepare(canvas,(c,w,h)=>{const left=Math.min(145,w*.38),top=18,row=(h-32)/Math.max(1,labels.length),maxWidth=w-left-35,pts=[];c.font='12px Arial';c.textBaseline='middle';labels.forEach((label,i)=>{const y=top+row*(i+.5),v=Math.max(0,Math.min(100,values[i]||0)),bw=maxWidth*v/100;c.fillStyle=palette.text;c.textAlign='right';c.fillText(label,left-10,y);c.fillStyle='#eff0f5';c.fillRect(left,y-7,maxWidth,14);c.fillStyle=palette.line;c.fillRect(left,y-7,bw,14);c.textAlign='left';c.fillStyle=palette.text;c.fillText(`${v}%`,left+bw+6,y);pts.push({x:left+bw,y,label:`${label} : ${v} %`})});return pts});
  }
  function line(canvas,labels,values,unit='%'){
    prepare(canvas,(c,w,h)=>{const l=42,r=14,t=18,b=30,cw=w-l-r,ch=h-t-b,pts=[],max=unit==='%'?100:Math.max(10,Math.ceil(Math.max(0,...values)/10)*10),step=unit==='%'?20:Math.max(5,Math.ceil(max/5/5)*5);c.font='10px Arial';c.textAlign='right';c.textBaseline='middle';for(let tick=0;tick<=max;tick+=step){const y=t+ch*(1-tick/max);c.beginPath();c.moveTo(l,y);c.lineTo(w-r,y);c.strokeStyle=palette.grid;c.stroke();c.fillStyle=palette.text;c.fillText(`${tick}${unit}`,l-6,y)}const n=values.length;if(!n)return pts;c.beginPath();values.forEach((val,i)=>{const x=l+(n===1?cw/2:cw*i/(n-1)),v=Math.max(0,Math.min(max,val)),y=t+ch*(1-v/max);i?c.lineTo(x,y):c.moveTo(x,y);pts.push({x,y,label:`${labels[i]} : ${val} ${unit}`})});c.strokeStyle=palette.line;c.lineWidth=2;c.stroke();pts.forEach(p=>{c.beginPath();c.arc(p.x,p.y,3.5,0,Math.PI*2);c.fillStyle=palette.line;c.fill()});c.textAlign='center';c.textBaseline='top';const stride=Math.max(1,Math.ceil(n/7));labels.forEach((label,i)=>{if(i%stride===0||i===n-1)c.fillText(label,l+(n===1?cw/2:cw*i/(n-1)),h-b+7)});return pts});
  }
  function columns(canvas,labels,values,unit='h'){
    prepare(canvas,(c,w,h)=>{const left=38,right=12,top=18,bottom=34,cw=w-left-right,ch=h-top-bottom,pts=[],n=values.length;
      const largest=Math.max(0,...values.map(v=>Number(v)||0));
      const max=Math.max(1,Math.ceil(largest*2)/2);
      const step=max<=2?0.5:max<=5?1:Math.ceil(max/5);
      c.font='10px Arial';c.textAlign='right';c.textBaseline='middle';
      for(let tick=0;tick<=max+0.0001;tick+=step){const y=top+ch*(1-tick/max);c.beginPath();c.moveTo(left,y);c.lineTo(w-right,y);c.strokeStyle=palette.grid;c.stroke();c.fillStyle=palette.text;c.fillText(String(Number(tick.toFixed(1)))+unit,left-7,y)}
      if(!n)return pts;
      const slot=cw/n,barWidth=Math.min(42,slot*.56);
      values.forEach((raw,i)=>{const v=Math.max(0,Number(raw)||0),barHeight=ch*v/max,x=left+slot*(i+.5)-barWidth/2,y=top+ch-barHeight;
        c.fillStyle=palette.line;c.beginPath();if(c.roundRect)c.roundRect(x,y,barWidth,Math.max(2,barHeight),6);else c.rect(x,y,barWidth,Math.max(2,barHeight));c.fill();
        c.fillStyle=palette.text;c.textAlign='center';c.textBaseline='top';c.fillText(labels[i],left+slot*(i+.5),h-bottom+9);
        pts.push({x:left+slot*(i+.5),y,label:labels[i]+' : '+v.toFixed(1)+' '+unit});
      });
      return pts;
    });
  }
  window.ICCharts={radar,bars,line,columns};
})();
