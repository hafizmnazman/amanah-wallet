import { config } from "@/config";

import { httpApi } from "./http";
import { createMockApi, type MockControls } from "./mock";
import type { AmanahApi } from "./types";

const mockApi = config.mock ? createMockApi() : null;

/** The backend the app talks to: lane B's HTTP API, or the in-browser mock when VITE_MOCK_API=1. */
export const api: AmanahApi = mockApi ?? httpApi(config.apiUrl);

/** Mock-only controls, such as raising the posture to show the banner. Null against a real backend. */
export const mockControls: MockControls | null = mockApi?.controls ?? null;

export * from "./types";
