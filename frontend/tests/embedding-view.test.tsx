/* Mathematical coordinates only; no fabricated medical observations. */
import { expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import EmbeddingView, { rotatePoint } from "../app/components/embedding-view";

it("rotates around the origin preserving three-dimensional distance", () => {
  expect(rotatePoint([1, 0, 0], 90, 0)[2]).toBeCloseTo(-1);
  expect(rotatePoint([0, 0, 1], 90, 0)[0]).toBeCloseTo(1);
  const rotated = rotatePoint([2, -4, 7], 37, -28);
  expect(Math.hypot(...rotated)).toBeCloseTo(Math.sqrt(69));
});
it("uses actual third coordinates and responds to keyboard-accessible rotation controls", () => {
  const { container } = render(
    <EmbeddingView
      coordinates={[
        [0, 0, 1],
        [0, 0, -1],
      ]}
      method="pca"
      variance={[0.7, 0.2, 0.1]}
    />,
  );
  const circle = container.querySelector('[data-row="1"]')!;
  const initialX = circle.getAttribute("cx");
  fireEvent.change(
    screen.getByRole("slider", { name: /Horizontal rotation/ }),
    { target: { value: "90" } },
  );
  expect(circle.getAttribute("cx")).not.toEqual(initialX);
  expect(screen.getByText("70.00%")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Inspect input row"), {
    target: { value: "2" },
  });
  expect(
    screen.getByText(
      /Input row 2: Component 1: 0.00000; Component 2: 0.00000; Component 3: -1.00000/,
    ),
  ).toBeInTheDocument();
});
it("rejects invalid coordinates and discloses a bounded display subset", () => {
  const { rerender, container } = render(
    <EmbeddingView coordinates={[[NaN, 0]]} method="pca" />,
  );
  expect(screen.getByText(/missing or invalid/)).toBeInTheDocument();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  rerender(
    <EmbeddingView
      coordinates={Array.from({ length: 2101 }, (_, i) => [i, -i])}
      method="pca"
    />,
  );
  expect(screen.getByText(/not a statistical sample/)).toBeInTheDocument();
  expect(container.querySelectorAll("circle")).toHaveLength(2000);
  expect(screen.queryByRole("slider")).not.toBeInTheDocument();
});
