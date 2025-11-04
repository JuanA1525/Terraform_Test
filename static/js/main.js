// Konami code Easter egg
(function(){
  const sequence = ["ArrowUp","ArrowUp","ArrowDown","ArrowDown","ArrowLeft","ArrowRight","ArrowLeft","ArrowRight","b","a"];
  let idx = 0;
  window.addEventListener('keydown', (e)=>{
    const key = e.key;
    if(key === sequence[idx]){
      idx++;
      if(idx === sequence.length){
        idx = 0;
        triggerEaster();
      }
    }else{
      idx = 0;
    }
  });

  function triggerEaster(){
    // Overlay
    let overlay = document.getElementById('easter-overlay');
    if(!overlay){
      overlay = document.createElement('div');
      overlay.id = 'easter-overlay';
      overlay.innerHTML = '<div class="bubble">EA SPORTS\n<small class="d-block text-secondary">It\'s in the game</small></div>';
      document.body.appendChild(overlay);
      overlay.addEventListener('click', ()=> overlay.style.display='none');
    }
    overlay.style.display = 'flex';

    // Confetti blast
    try{
      confetti({ particleCount: 200, spread: 80, origin: { y: 0.6 } });
    }catch{}

    // Sound
    const audio = new Audio('https://cdn.pixabay.com/download/audio/2021/08/09/audio_1b1e201d7c.mp3?filename=game-start-6104.mp3');
    audio.volume = 0.5;
    audio.play().catch(()=>{});
  }
})();

// Auto-confetti when champion banner present
(function(){
  const alert = document.querySelector('[data-champion]');
  if(alert){
    try{
      setTimeout(()=> confetti({ particleCount: 150, spread: 70 }), 400);
    }catch{}
  }
})();

// Bootstrap toast auto-dismiss
(function(){
  document.querySelectorAll('.toast').forEach(t=>{
    setTimeout(()=> t.classList.remove('show'), 4000);
  });
})();
