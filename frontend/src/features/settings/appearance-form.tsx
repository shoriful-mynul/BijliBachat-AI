"use client";

import { Card } from "@/components/ui/card";
import { SectionHeader } from "@/components/ui/section-header";
import { Select } from "@/components/ui/select";
import { useTheme } from "@/hooks/use-theme";
import { isTheme } from "@/lib/theme";

const options = [
  { value: "dark", label: "Dark — Blue Hour" },
  { value: "light", label: "Light" },
] as const;

export function AppearanceForm() {
  const { theme, setTheme } = useTheme();

  return (
    <Card>
      <SectionHeader
        title="Appearance"
        description="Blue Hour dark is the brand default. This choice stays in this browser."
      />
      <Select
        className="mt-4 max-w-sm"
        label="Theme"
        value={theme}
        options={options}
        hint="Nothing on this screen is sent to a server."
        onChange={(event) => {
          if (isTheme(event.target.value)) {
            setTheme(event.target.value);
          }
        }}
      />
    </Card>
  );
}
