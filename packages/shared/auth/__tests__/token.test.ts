import { clearToken, getToken, setToken, TOKEN_STORAGE_KEY } from "../token";

describe("token storage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.cookie = "healthcore_access_token=; path=/; max-age=0";
    Object.defineProperty(window, "location", {
      value: { hostname: "localhost" },
      writable: true,
    });
  });

  it("round-trips token via localStorage and cookie on localhost", () => {
    setToken("abc123");
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBe("abc123");
    expect(getToken()).toBe("abc123");
  });

  it("clearToken removes localStorage and cookie on localhost", () => {
    setToken("abc123");
    clearToken();
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
    expect(document.cookie).not.toContain("healthcore_access_token=abc123");
    expect(getToken()).toBeNull();
  });
});
