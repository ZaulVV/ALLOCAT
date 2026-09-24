import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import React from "react";
import { Login } from "./main.jsx";

describe("ALLOCAT frontend", () => {
  it("renders a root container", () => {
    render(<Login onLogin={() => {}} />);
    expect(document.body).toHaveTextContent("ALLOCAT");
    expect(document.body).toHaveTextContent("Iniciar sesión");
  });
});
