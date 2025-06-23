function startTraining() {
  fetch('/api/train', {
    method: 'POST'
  })
    .then(res => res.json())
    .then(data => {
      alert(data.message || 'Training started!');
    })
    .catch(err => {
      alert('Training failed.');
      console.error(err);
    });
}
