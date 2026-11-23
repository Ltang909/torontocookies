(function(){
  // Prefill the package on /order/?package=...
  var sel=document.getElementById('package');
  if(sel){var m=location.search.match(/[?&]package=([\w-]+)/);if(m){sel.value=m[1];}}
  // Lightweight PostHog events (autocapture also records clicks)
  document.addEventListener('click',function(ev){
    var a=ev.target.closest('[data-track]');
    if(a&&window.posthog){posthog.capture(a.getAttribute('data-track'),{package:a.getAttribute('data-package')||null,href:a.getAttribute('href')});}
  });
  var f=document.querySelector('form[data-track-form]');
  if(f){f.addEventListener('submit',function(){
    if(window.posthog){var d=new FormData(f);posthog.capture(f.getAttribute('data-track-form'),{package:d.get('package'),area:d.get('area'),dietary:d.get('dietary')});}
  });}
})();
