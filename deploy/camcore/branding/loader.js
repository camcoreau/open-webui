(() => {
  const applyCamCoreIdentity = () => {
    document.documentElement.dataset.camcoreBranding = 'true';

    const theme = document.querySelector('meta[name="theme-color"]');
    if (theme) theme.setAttribute('content', '#071014');

    document
      .querySelectorAll('link[rel~="icon"], link[rel="shortcut icon"]')
      .forEach((link) => link.setAttribute('href', '/static/camcore-mark.svg'));

    const touchIcon = document.querySelector('link[rel="apple-touch-icon"]');
    if (touchIcon) touchIcon.setAttribute('href', '/static/camcore-mark.svg');
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyCamCoreIdentity, { once: true });
  } else {
    applyCamCoreIdentity();
  }
})();
