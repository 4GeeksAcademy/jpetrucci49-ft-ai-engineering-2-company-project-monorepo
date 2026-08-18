import { buildAuthenticatedAppUrl, consumeTokenFromHash } from "../cross-app";
import { clearToken, setToken } from "../token";

describe("cross-app session handoff", () => {
  beforeEach(() => {
    window.localStorage.clear();
    clearToken();
    Object.defineProperty(window, "location", {
      value: {
        hostname: "localhost",
        hash: "",
        pathname: "/dashboard",
        search: "",
      },
      writable: true,
    });
    window.history.replaceState = jest.fn();
  });

  it("appends access_token hash when token is present", () => {
    setToken("session-token");
    const url = buildAuthenticatedAppUrl("http://localhost:3002/reports");
    expect(url).toContain("#access_token=");
    expect(url).toContain(encodeURIComponent("session-token"));
  });

  it("returns false when hash is missing", () => {
    expect(consumeTokenFromHash()).toBe(false);
  });
});
