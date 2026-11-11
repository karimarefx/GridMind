import type { Ref } from "react";
import { DiagnosisUpload } from "./DiagnosisUpload";

export function Diagnosis({ titleRef }: { titleRef: Ref<HTMLHeadingElement> }) {
  return <DiagnosisUpload titleRef={titleRef} />;
}
