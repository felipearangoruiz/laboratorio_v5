"use client";

import Link from "next/link";
import {
  Settings,
  CreditCard,
  FileText,
  UserCircle,
  ChevronLeft,
  ChevronRight,
  Building2,
} from "lucide-react";

interface SidebarProps {
  open: boolean;
  onToggle: () => void;
  orgId: string;
}

const NAV_ITEMS = [
  { icon: Settings, label: "Settings",   href: "settings" },
  { icon: CreditCard, label: "Billing",  href: "billing" },
  { icon: FileText,  label: "Documentos",href: "documents" },
];

export default function Sidebar({ open, onToggle, orgId }: SidebarProps) {
  return (
    <div
      className={`flex flex-col transition-all duration-200 border-r ${
        open ? "w-48" : "w-14"
      }`}
      style={{
        background: "rgba(13,13,20,0.95)",
        borderRightColor: "rgba(255,255,255,0.08)",
      }}
    >
      {/* Org mark + toggle */}
      <div
        className="px-3 py-3 flex items-center gap-2 border-b"
        style={{ borderBottomColor: "rgba(255,255,255,0.08)" }}
      >
        <div className="w-8 h-8 bg-[#C2410C] rounded-md flex items-center justify-center flex-shrink-0">
          <Building2 className="w-4 h-4 text-white" strokeWidth={1.5} />
        </div>
        {open && (
          <span className="text-sm font-semibold text-white/80 truncate flex-1">
            Mi Org
          </span>
        )}
        <button
          onClick={onToggle}
          className="text-white/30 hover:text-white/60 flex-shrink-0 transition-colors"
        >
          {open ? (
            <ChevronLeft className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-2 space-y-0.5">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={`/org/${orgId}/${item.href}`}
            className="flex items-center gap-2.5 px-3 py-2 text-white/40 hover:text-white/80 hover:bg-white/5 rounded-md mx-1.5 transition-colors"
          >
            <item.icon className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} />
            {open && (
              <span className="text-sm truncate">{item.label}</span>
            )}
          </Link>
        ))}
      </nav>

      {/* Account */}
      <div className="border-t py-2" style={{ borderTopColor: "rgba(255,255,255,0.08)" }}>
        <Link
          href="/account"
          className="flex items-center gap-2.5 px-3 py-2 text-white/40 hover:text-white/80 hover:bg-white/5 rounded-md mx-1.5 transition-colors"
        >
          <UserCircle className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} />
          {open && <span className="text-sm truncate">Cuenta</span>}
        </Link>
      </div>
    </div>
  );
}
