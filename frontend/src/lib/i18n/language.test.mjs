import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import {
  applyLanguage,
  LANGUAGE_STORAGE_KEY,
  readLanguageValue,
  serializeLanguage,
} from "./language.ts";
import { en, messageKeyForEnglish, translate, ur } from "./messages.ts";

const root = new URL("../../", import.meta.url);

describe("language preference", () => {
  it("defaults to English when nothing is stored", () => {
    assert.deepEqual(readLanguageValue(null), { language: "en", recognized: true });
    assert.equal(translate("en", "nav.overview.label"), "Overview");
  });

  it("accepts Urdu and returns to English", () => {
    assert.deepEqual(readLanguageValue(serializeLanguage("ur")), {
      language: "ur",
      recognized: true,
    });
    assert.deepEqual(readLanguageValue(serializeLanguage("en")), {
      language: "en",
      recognized: true,
    });
    assert.equal(translate("ur", "nav.overview.label"), "جائزہ");
    assert.equal(translate("en", "nav.settings.label"), "Settings");
  });

  it("keeps the saved value in the versioned language key only", () => {
    const storage = new Map();
    storage.set("bb-theme", "light");
    storage.set(LANGUAGE_STORAGE_KEY, serializeLanguage("ur"));
    const read = readLanguageValue(storage.get(LANGUAGE_STORAGE_KEY));
    assert.equal(read.language, "ur");
    assert.equal(storage.get("bb-theme"), "light");
  });

  it("falls back to English when the stored value is corrupt or unsupported", () => {
    for (const raw of ["{", "fr", JSON.stringify("fr"), JSON.stringify({ language: "ar" }), "undefined"]) {
      const read = readLanguageValue(raw);
      assert.equal(read.language, "en");
      assert.equal(read.recognized, false);
    }
  });

  it("sets document lang and dir", () => {
    const english = { lang: "", dir: "" };
    applyLanguage("en", english);
    assert.equal(english.lang, "en");
    assert.equal(english.dir, "ltr");

    const urdu = { lang: "", dir: "" };
    applyLanguage("ur", urdu);
    assert.equal(urdu.lang, "ur");
    assert.equal(urdu.dir, "rtl");
  });

  it("falls back to English when a Urdu string is missing at runtime", () => {
    const key = "nav.history.label";
    assert.equal(translate("ur", key), ur[key]);
    assert.equal(
      translate("ur", key, undefined, { en, ur: { ...ur, [key]: "" } }),
      en[key],
    );
  });

  it("covers the same keys in both languages and translates navigation", () => {
    const keys = Object.keys(en);
    assert.deepEqual(Object.keys(ur).sort(), keys.sort());
    for (const key of ["nav.history.label", "nav.bill.label", "nav.settings.label", "trust.verified"]) {
      assert.notEqual(ur[key], en[key]);
    }
    assert.equal(messageKeyForEnglish("The API address is not configured."), "common.apiMissing");
    assert.equal(translate("ur", "common.apiMissing"), "API کا پتہ سیٹ نہیں ہے۔");
    assert.equal(messageKeyForEnglish("not a catalog sentence"), null);
  });
});

describe("accessible controls", () => {
  it("associates form errors with inputs", () => {
    const input = readFileSync(new URL("components/ui/input.tsx", root), "utf8");
    const select = readFileSync(new URL("components/ui/select.tsx", root), "utf8");
    for (const source of [input, select]) {
      assert.match(source, /htmlFor=\{fieldId\}/);
      assert.match(source, /aria-invalid=\{error \? true : undefined\}/);
      assert.match(source, /aria-describedby=\{describedBy\}/);
      assert.match(source, /role="alert"/);
    }
  });

  it("keeps navigation and dialogs keyboard reachable", () => {
    const mobile = readFileSync(new URL("components/layout/mobile-navigation.tsx", root), "utf8");
    const shell = readFileSync(new URL("components/layout/app-shell.tsx", root), "utf8");
    assert.match(mobile, /type="button"/);
    assert.match(mobile, /event\.key === "Escape"/);
    assert.match(mobile, /role="dialog"/);
    assert.match(mobile, /aria-modal="true"/);
    assert.match(shell, /href="#main"/);
    assert.match(shell, /<main id="main"/);
  });

  it("gives charts a text alternative", () => {
    for (const file of [
      "features/history/history-chart.tsx",
      "features/prediction/forecast-chart.tsx",
      "features/appliances/usage-chart.tsx",
      "components/dashboard/consumption-chart.tsx",
    ]) {
      const source = readFileSync(new URL(file, root), "utf8");
      assert.match(source, /<caption/);
      assert.match(source, /role="img"/);
      assert.match(source, /chart-ltr/);
    }
  });
});
