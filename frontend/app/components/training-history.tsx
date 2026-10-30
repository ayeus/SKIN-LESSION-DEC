"use client";
import type { ComponentType } from "react";
type Props = {
  history: Record<string, any>[];
  Chart: ComponentType<{ data: any[]; keys: string[] }>;
};
export default function TrainingHistory({ history, Chart }: Props) {
  if (!history.length) return null;
  const cnn = history.every(
    (h) =>
      typeof h.train?.loss === "number" &&
      typeof h.validation?.loss === "number",
  );
  const ner = history.every(
    (h) => typeof h.loss === "number" && typeof h.validation?.f1 === "number",
  );
  const segmentation = history.every(
    (h) => typeof h.loss === "number" && typeof h.validation?.dice === "number",
  );
  if (segmentation)
    return (
      <>
        <h3>Segmentation training loss</h3>
        <Chart
          data={history.map((h) => ({ index: h.epoch, training_loss: h.loss }))}
          keys={["training_loss"]}
        />
        <h3>Segmentation validation Dice</h3>
        <Chart
          data={history.map((h) => ({
            index: h.epoch,
            validation_dice: h.validation.dice,
          }))}
          keys={["validation_dice"]}
        />
      </>
    );
  if (cnn)
    return (
      <>
        <h3>Training and validation loss</h3>
        <Chart
          data={history.map((h) => ({
            index: h.epoch,
            train_loss: h.train.loss,
            validation_loss: h.validation.loss,
          }))}
          keys={["train_loss", "validation_loss"]}
        />
      </>
    );
  if (ner)
    return (
      <>
        <h3>Clinical NER training loss</h3>
        <Chart
          data={history.map((h) => ({ index: h.epoch, training_loss: h.loss }))}
          keys={["training_loss"]}
        />
        <h3>Clinical NER validation exact-span F1</h3>
        <Chart
          data={history.map((h) => ({
            index: h.epoch,
            validation_f1: h.validation.f1,
          }))}
          keys={["validation_f1"]}
        />
      </>
    );
  return (
    <p className="notice">
      This run has an unsupported history schema. Inspect the exact recorded
      history in its JSON report.
    </p>
  );
}
