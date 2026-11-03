const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include"
  });

  if (!response.ok) {
    const responseText = await response.text();
    let message = responseText || `Request failed with status ${response.status}.`;
    try {
      const errorBody = JSON.parse(responseText);
      if (typeof errorBody.detail === "string") {
        message = errorBody.detail;
      }
    } catch {
      // Retain a non-JSON response body as the error message.
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return null;
  }
  if (response.status === 205 || response.headers.get("content-length") === "0") {
    return null;
  }
  return response.json();
}
