"use client";

import Link from "next/link";
import {
  Building2,
  Settings,
  CreditCard,
  FileText,
  UserCircle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

interface SidebarProps {
  open: boolean;
  onToggle: () => void;
  orgId: string;
}

const NAV_ITEMS = [
  { icon: Settings, label: "Settings", href: "settings" },
  { icon: CreditCard, label: "Billing", href: "billing" },
  { icon: FileText, label: "Documentos", href: "documents" },
];

export default function Sidebar({ open, onToggle, orgId }: SidebarProps) {
  return (
    <div
      className={`flex flex-col bg-white border-r border-gray-200 transition-all duration-200 ${
        open ? "w-48" : "w-14"
      }`}
    >
      {/* Org name / toggle */}
      <div className="px-3 py-3 border-b border-gray-100 flex items-center gap-2">
        <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center flex-shrink-0">
          <Building2 className="w-4 h-4 text-white" />
        </div>
        {open && (
          <span className="text-sm font-semibold text-gray-900 truncate flex-1">
            Mi Org
          </span>
        )}
        <button
          onClick={onToggle}
          className="text-gray-400 hover:text-gray-600 flex-shrink-0"
        >
          {open ? (
            <ChevronLeft className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Nav items */}
      <nav className="flex-1 py-2 space-y-0.5">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={`/org/${orgId}/${item.href}`}
            className="flex items-center gap-2.5 px-3 py-2 text-gray-600 hover:bg-gray-50 hover:text-gray-900 rounded-lg mx-1.5"
          >
            <item.icon className="w-4 h-4 flex-shrink-0" />
            {open && (
              <span className="text-sm truncate">{item.label}</span>
            )}
          </Link>
        ))}
      </nav>

      {/* Account */}
      <div className="border-t border-gray-100 py-2">
        <Link
          href="/account"
          className="flex items-center gap-2.5 px-3 py-2 text-gray-600 hover:bg-gray-50 hover:text-gray-900 rounded-lg mx-1.5"
        >
          <UserCircle className="w-4 h-4 flex-shrink-0" />
          {open && <span className="text-sm truncate">Cuenta</span>}
        </Link>
      </div>
    </div>
  );
}
