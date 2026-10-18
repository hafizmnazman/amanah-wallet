/** The three demo funds and programmes of plan section 10. */
export interface Programme {
  code: string;
  name: string;
  fund: string;
  capUsdc: number;
}

export const PROGRAMMES: Programme[] = [
  { code: "ZKT-IPOH-FAKIR-M", name: "Ipoh fakir monthly aid", fund: "Zakat Fund", capUsdc: 200 },
  { code: "REL-PERAK-FLOOD", name: "Perak flood relief", fund: "Flood Relief Fund", capUsdc: 300 },
  { code: "EDU-BURSARY-S1", name: "Semester bursary", fund: "Education Bursary Fund", capUsdc: 500 },
];
