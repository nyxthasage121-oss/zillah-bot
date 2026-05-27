// Kindred roster: clan filter + name search.
document.addEventListener('DOMContentLoaded', () => {
  const buttons = $$('.filter');
  const cards = $$('.kindred-card');
  buttons.forEach(b => {
    b.addEventListener('click', () => {
      buttons.forEach(x => x.classList.remove('filter-active'));
      b.classList.add('filter-active');
      const clan = b.dataset.clan;
      cards.forEach(c => {
        c.style.display = (clan === 'all' || c.dataset.clan === clan) ? '' : 'none';
      });
    });
  });

  const search = $('input[type="search"]');
  if (search) {
    search.addEventListener('input', () => {
      const q = search.value.toLowerCase();
      cards.forEach(c => {
        c.style.display = c.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }
});
