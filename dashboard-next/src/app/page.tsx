import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { KindredFilterBar } from "@/components/kindred-filter-bar";
import { ROSTER } from "@/lib/mock-data";

export default function HomePage() {
  return (
    <>
      <SiteHeader domainName="St. Augustine by Night" username="storyteller_amelia" active="kindred" />
      <main className="max-w-[1440px] mx-auto px-10 py-10">
        <KindredFilterBar roster={ROSTER} />
      </main>
      <SiteFooter />
    </>
  );
}
