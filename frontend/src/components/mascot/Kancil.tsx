import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Sang Kancil, the mouse-deer of Malay folklore who outwits every trickster: Amanah's guide. A chibi
 * mouse-deer drawn in flat shapes, with the white chevrons mouse-deer carry on the throat. One pose per
 * moment: waving hello, happy when a payout lands, alert when it spots a trick, thinking while the checks
 * run, asleep when nothing waits.
 */
export type KancilPose = "wave" | "happy" | "alert" | "thinking" | "sleep" | "calm";
export type KancilProp = "key" | "shield" | null;

const COAT = "#d6884f";
const COAT_DARK = "#b96b36";
const LEG = "#c57a43";
const CREAM = "#fff3e4";
const EAR = "#f6b9a2";
const INK = "#2f2622";
const HOOF = "#4a3428";

export function Kancil({
  pose = "calm",
  prop = null,
  size = 120,
  className,
  title = "Sang Kancil, Amanah's guide",
}: {
  pose?: KancilPose;
  prop?: KancilProp;
  size?: number;
  className?: string;
  title?: string;
}) {
  return (
    <svg
      viewBox="0 0 200 220"
      width={size}
      height={(size * 220) / 200}
      role="img"
      aria-label={title}
      className={cn("shrink-0 select-none", className)}
    >
      <title>{title}</title>
      <ellipse cx="100" cy="210" rx="46" ry="7" fill="#000" opacity="0.08" />
      {/* Back legs, behind the body */}
      <rect x="66" y="170" width="10" height="30" rx="5" fill={COAT_DARK} />
      <rect x="124" y="170" width="10" height="30" rx="5" fill={COAT_DARK} />
      <ellipse cx="71" cy="201" rx="6.5" ry="4.5" fill={HOOF} />
      <ellipse cx="129" cy="201" rx="6.5" ry="4.5" fill={HOOF} />
      {/* Body */}
      <ellipse cx="100" cy="156" rx="38" ry="33" fill={COAT} />
      <path d="M84 147 L100 157 L116 147" stroke="#fff" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <path d="M87 162 L100 170 L113 162" stroke="#fff" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      {/* Front legs; the wave lifts the right one */}
      <rect x="82" y="176" width="10" height="28" rx="5" fill={LEG} />
      <ellipse cx="87" cy="205" rx="6.5" ry="4.5" fill={HOOF} />
      {pose === "wave" ? (
        <g transform="rotate(-128 113 176)">
          <rect x="108" y="176" width="10" height="30" rx="5" fill={LEG} />
          <ellipse cx="113" cy="207" rx="6.5" ry="4.5" fill={HOOF} />
        </g>
      ) : (
        <>
          <rect x="108" y="176" width="10" height="28" rx="5" fill={LEG} />
          <ellipse cx="113" cy="205" rx="6.5" ry="4.5" fill={HOOF} />
        </>
      )}
      {/* Ears, behind the head */}
      <ellipse cx="56" cy="50" rx="15" ry="30" transform="rotate(-38 56 50)" fill={COAT} />
      <ellipse cx="58" cy="52" rx="7.5" ry="19" transform="rotate(-38 58 52)" fill={EAR} />
      <ellipse cx="144" cy="50" rx="15" ry="30" transform="rotate(38 144 50)" fill={COAT} />
      <ellipse cx="142" cy="52" rx="7.5" ry="19" transform="rotate(38 142 52)" fill={EAR} />
      {/* Head */}
      <ellipse cx="100" cy="88" rx="55" ry="49" fill={COAT} />
      <path d="M86 43 Q100 36 114 43 Q100 52 86 43Z" fill={COAT_DARK} />
      <ellipse cx="84" cy="60" rx="17" ry="9" fill="#fff" opacity="0.16" />
      <ellipse cx="100" cy="111" rx="31" ry="21" fill={CREAM} />
      <ellipse cx="63" cy="106" rx="9" ry="6" fill="#f59a85" opacity="0.5" />
      <ellipse cx="137" cy="106" rx="9" ry="6" fill="#f59a85" opacity="0.5" />
      <Eyes pose={pose} />
      <path d="M92 101 Q100 96 108 101 Q107 107 100 109 Q93 107 92 101Z" fill="#3b2a20" />
      <ellipse cx="97" cy="101" rx="2.6" ry="1.6" fill="#fff" opacity="0.7" />
      <Mouth pose={pose} />
      {prop === "key" && <Key />}
      {prop === "shield" && <Shield />}
      {pose === "alert" && <Bang />}
      {pose === "thinking" && <Thought />}
      {pose === "sleep" && <Zs />}
    </svg>
  );
}

function Eyes({ pose }: { pose: KancilPose }) {
  if (pose === "happy") {
    return (
      <g stroke={INK} strokeWidth="5.5" strokeLinecap="round" fill="none">
        <path d="M68 89 Q78 76 88 89" />
        <path d="M112 89 Q122 76 132 89" />
      </g>
    );
  }
  if (pose === "sleep") {
    return (
      <g stroke={INK} strokeWidth="5" strokeLinecap="round" fill="none">
        <path d="M69 86 Q78 93 87 86" />
        <path d="M113 86 Q122 93 131 86" />
      </g>
    );
  }
  const lookUp = pose === "thinking" ? -4 : 0;
  const lookSide = pose === "thinking" ? 3 : 0;
  const big = pose === "alert" ? 1.12 : 1;
  return (
    <g>
      {pose === "alert" && (
        <g stroke="#7a4520" strokeWidth="5" strokeLinecap="round">
          <path d="M65 64 L88 70" />
          <path d="M135 64 L112 70" />
        </g>
      )}
      {pose === "thinking" && <path d="M112 64 Q122 58 133 64" stroke="#7a4520" strokeWidth="5" strokeLinecap="round" fill="none" />}
      {[78, 122].map((cx) => (
        <g key={cx}>
          <ellipse cx={cx} cy={85} rx={10.5 * big} ry={12.5 * big} fill={INK} />
          <circle cx={cx - 3.5 + lookSide} cy={79.5 + lookUp} r={4.2} fill="#fff" />
          <circle cx={cx + 3 + lookSide} cy={90 + lookUp} r={2} fill="#fff" opacity="0.85" />
        </g>
      ))}
    </g>
  );
}

function Mouth({ pose }: { pose: KancilPose }) {
  if (pose === "happy" || pose === "wave") {
    return (
      <g>
        <path d="M89 114 Q100 130 111 114 Z" fill="#7a2e2a" />
        <path d="M94 121 Q100 127 106 121 Q100 118 94 121Z" fill="#f07c7c" />
      </g>
    );
  }
  if (pose === "alert") return <ellipse cx="100" cy="119" rx="5" ry="6" fill="#3b2a20" />;
  if (pose === "thinking") return <path d="M93 118 Q101 115 108 119" stroke="#3b2a20" strokeWidth="3.5" strokeLinecap="round" fill="none" />;
  if (pose === "sleep") return <path d="M95 117 Q100 120 105 117" stroke="#3b2a20" strokeWidth="3" strokeLinecap="round" fill="none" />;
  return <path d="M91 115 Q100 123 109 115" stroke="#3b2a20" strokeWidth="3.5" strokeLinecap="round" fill="none" />;
}

/** The vault's key, held across the chest. */
function Key() {
  return (
    <g transform="translate(104 150) rotate(-24)">
      <circle cx="0" cy="0" r="11" fill="none" stroke="#b97f00" strokeWidth="9" />
      <circle cx="0" cy="0" r="11" fill="none" stroke="#f2ab13" strokeWidth="5.5" />
      <rect x="9" y="-4" width="34" height="8" rx="4" fill="#f2ab13" stroke="#b97f00" strokeWidth="1.5" />
      <rect x="31" y="2" width="6" height="10" rx="2.5" fill="#f2ab13" stroke="#b97f00" strokeWidth="1.5" />
      <rect x="21" y="2" width="6" height="8" rx="2.5" fill="#f2ab13" stroke="#b97f00" strokeWidth="1.5" />
    </g>
  );
}

/** A guardian's shield with a tick, on the chest. */
function Shield() {
  return (
    <g transform="translate(100 156)">
      <path d="M0 -20 L18 -13 L16 6 Q12 18 0 24 Q-12 18 -16 6 L-18 -13 Z" fill="#18a873" stroke="#0f8358" strokeWidth="3" strokeLinejoin="round" />
      <path d="M-8 1 L-2 8 L9 -6" stroke="#fff" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </g>
  );
}

function Bang() {
  return (
    <g transform="translate(164 30)">
      <circle r="17" fill="#ef5350" stroke="#c13434" strokeWidth="3" />
      <rect x="-3" y="-10" width="6" height="13" rx="3" fill="#fff" />
      <circle cy="8" r="3.4" fill="#fff" />
    </g>
  );
}

function Thought() {
  return (
    <g fill="#fff" stroke="#d9ccb6" strokeWidth="2.5">
      <circle cx="152" cy="40" r="5" />
      <circle cx="166" cy="26" r="8" />
      <circle cx="184" cy="10" r="10" />
    </g>
  );
}

function Zs() {
  return (
    <g fill="#776c5d" fontFamily="'Nunito Variable', sans-serif" fontWeight="900">
      <text x="150" y="44" fontSize="22">z</text>
      <text x="168" y="26" fontSize="16">z</text>
    </g>
  );
}

/** Kancil with a speech bubble: the guide's voice, short and warm. */
export function KancilSays({
  pose = "calm",
  prop = null,
  size = 72,
  children,
  className,
  tone = "default",
}: {
  pose?: KancilPose;
  prop?: KancilProp;
  size?: number;
  children: ReactNode;
  className?: string;
  tone?: "default" | "alert" | "good";
}) {
  const toneClass =
    tone === "alert" ? "border-danger/30 bg-danger-light" : tone === "good" ? "border-primary/30 bg-primary-light" : "border-border bg-surface";
  return (
    <div className={cn("flex items-end gap-3", className)}>
      <Kancil pose={pose} prop={prop} size={size} />
      <div className={cn("bubble-tail-left mb-3 rounded-2xl border-2 px-4 py-3 text-sm leading-relaxed text-ink", toneClass)}>{children}</div>
    </div>
  );
}
