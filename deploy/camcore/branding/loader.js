(() => {
	const PRODUCT_NAME = 'Jarvis | CamCore AI';
	const THEME_COLOR = '#071014';
	const FAVICON_SVG = '/static/favicon.svg';
	const FAVICON_PNG = '/static/favicon.png';
	const TOUCH_ICON = '/static/apple-touch-icon.png';
	const MANIFEST = '/static/camcore-manifest.json';

	const upsertMeta = (name, content) => {
		let meta = document.querySelector(`meta[name="${name}"]`);
		if (!meta) {
			meta = document.createElement('meta');
			meta.setAttribute('name', name);
			document.head.appendChild(meta);
		}
		meta.setAttribute('content', content);
	};

	const cleanTitle = (value) => {
		if (!value) return PRODUCT_NAME;

		return value
			.replaceAll(`${PRODUCT_NAME} (Open WebUI)`, PRODUCT_NAME)
			.replaceAll('Open WebUI', PRODUCT_NAME)
			.trim();
	};

	const applyTitle = () => {
		const cleaned = cleanTitle(document.title);
		if (document.title !== cleaned) document.title = cleaned;
	};

	const applyIcons = () => {
		document.querySelectorAll('link[rel~="icon"]').forEach((link) => {
			const isShortcut = link.rel.split(/\s+/).includes('shortcut');
			link.setAttribute('href', isShortcut ? FAVICON_PNG : FAVICON_SVG);
			link.setAttribute('type', isShortcut ? 'image/png' : 'image/svg+xml');
			link.removeAttribute('sizes');
		});

		let touchIcon = document.querySelector('link[rel="apple-touch-icon"]');
		if (!touchIcon) {
			touchIcon = document.createElement('link');
			touchIcon.setAttribute('rel', 'apple-touch-icon');
			document.head.appendChild(touchIcon);
		}
		touchIcon.setAttribute('href', TOUCH_ICON);
		touchIcon.setAttribute('sizes', '180x180');

		let manifest = document.querySelector('link[rel="manifest"]');
		if (!manifest) {
			manifest = document.createElement('link');
			manifest.setAttribute('rel', 'manifest');
			document.head.appendChild(manifest);
		}
		manifest.setAttribute('href', MANIFEST);
	};

	const applyManagedTheme = () => {
		try {
			localStorage.setItem('theme', 'dark');
		} catch (_) {
			// Storage can be unavailable in hardened/private browser contexts.
		}

		document.documentElement.classList.remove('light', 'her', 'oled-dark');
		document.documentElement.classList.add('dark');
		document.documentElement.style.removeProperty('--color-gray-800');
		document.documentElement.style.removeProperty('--color-gray-850');
		document.documentElement.style.removeProperty('--color-gray-900');
		document.documentElement.style.removeProperty('--color-gray-950');
	};

	const applyCamCoreIdentity = () => {
		document.documentElement.dataset.camcoreBranding = 'full';
		document.documentElement.dataset.camcoreProduct = 'jarvis';

		applyManagedTheme();
		applyIcons();
		applyTitle();

		upsertMeta('theme-color', THEME_COLOR);
		upsertMeta('application-name', PRODUCT_NAME);
		upsertMeta('apple-mobile-web-app-title', PRODUCT_NAME);
		upsertMeta('apple-mobile-web-app-capable', 'yes');
		upsertMeta('mobile-web-app-capable', 'yes');
	};

	applyCamCoreIdentity();

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', applyCamCoreIdentity, { once: true });
	}

	// Svelte updates <title> after the backend config arrives. Keep the visible
	// product identity CamCore-native without interfering with chat-specific titles.
	const titleElement = document.querySelector('title');
	if (titleElement) {
		new MutationObserver(applyTitle).observe(titleElement, {
			childList: true,
			characterData: true,
			subtree: true
		});
	}
})();
