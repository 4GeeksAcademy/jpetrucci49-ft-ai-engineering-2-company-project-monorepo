(function () {
  const root = document.documentElement;
  const toggles = document.querySelectorAll("[data-lang-toggle]");

  function setLanguage(lang) {
    const safeLang = lang === "es" ? "es" : "en";
    root.setAttribute("lang", safeLang);
    root.setAttribute("data-current-lang", safeLang);

    const titleKey = safeLang === "es" ? "data-title-es" : "data-title-en";
    const titleElement =
      document.getElementById("page-title") || document.querySelector("title");
    const localizedTitle =
      (titleElement && titleElement.getAttribute(titleKey)) ||
      root.getAttribute(titleKey);
    if (localizedTitle) {
      document.title = localizedTitle;
      if (titleElement) {
        titleElement.textContent = localizedTitle;
      }
    }

    document.querySelectorAll("[data-lang]").forEach((element) => {
      const isMatch = element.getAttribute("data-lang") === safeLang;
      element.hidden = !isMatch;
    });

    document
      .querySelectorAll("[data-placeholder-en][data-placeholder-es]")
      .forEach((element) => {
        const placeholder =
          safeLang === "es"
            ? element.getAttribute("data-placeholder-es")
            : element.getAttribute("data-placeholder-en");
        if (placeholder) {
          element.setAttribute("placeholder", placeholder);
        }
      });

    document
      .querySelectorAll("[data-label-en][data-label-es]")
      .forEach((element) => {
        const translatedText =
          safeLang === "es"
            ? element.getAttribute("data-label-es")
            : element.getAttribute("data-label-en");

        if (translatedText) {
          element.textContent = translatedText;
        }
      });

    toggles.forEach((toggle) => {
      const isActive = toggle.getAttribute("data-lang-toggle") === safeLang;
      toggle.setAttribute("aria-pressed", String(isActive));
      toggle.classList.toggle("font-semibold", isActive);
      toggle.classList.toggle("text-teal-700", isActive);
    });

    try {
      localStorage.setItem("preferredLang", safeLang);
    } catch (error) {
      // Ignore storage errors in restricted environments.
    }
  }

  toggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      setLanguage(toggle.getAttribute("data-lang-toggle"));
    });
  });

  let initialLang = "en";
  try {
    const persistedLang = localStorage.getItem("preferredLang");
    if (persistedLang === "en" || persistedLang === "es") {
      initialLang = persistedLang;
    }
  } catch (error) {
    initialLang = "en";
  }

  setLanguage(initialLang);
})();
