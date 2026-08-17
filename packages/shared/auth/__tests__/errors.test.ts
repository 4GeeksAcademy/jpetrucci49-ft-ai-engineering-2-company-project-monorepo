import { parseApiError, parseApiFieldErrors } from "../errors";

function mockResponse(
  body: unknown,
  options: { status?: number; statusText?: string; jsonThrows?: boolean } = {}
): Response {
  const { status = 400, statusText = "Bad Request", jsonThrows = false } = options;
  return {
    status,
    statusText,
    json: jsonThrows
      ? async () => {
          throw new Error("invalid json");
        }
      : async () => body,
  } as Response;
}

describe("parseApiError", () => {
  it("returns string detail from JSON body", async () => {
    const response = mockResponse({ detail: "Invalid credentials." });
    await expect(parseApiError(response)).resolves.toBe("Invalid credentials.");
  });

  it("falls back when body is not JSON", async () => {
    const response = mockResponse(null, {
      status: 502,
      statusText: "Bad Gateway",
      jsonThrows: true,
    });
    await expect(parseApiError(response)).resolves.toBe("Bad Gateway");
  });
});

describe("parseApiFieldErrors", () => {
  it("maps validation detail array to field errors", async () => {
    const response = mockResponse({
      detail: [{ loc: ["body", "email"], msg: "Invalid email", type: "value_error" }],
    });
    await expect(parseApiFieldErrors(response)).resolves.toEqual({
      email: "Invalid email",
    });
  });

  it("returns empty object for non-JSON body", async () => {
    const response = mockResponse(null, { status: 422, jsonThrows: true });
    await expect(parseApiFieldErrors(response)).resolves.toEqual({});
  });
});
