"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Trophy,
  LineChart,
  Brain,
  DollarSign,
  Globe,
  Activity,
  Menu,
  X,
} from "lucide-react";
import { useState } from "react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/matches", label: "Matches", icon: Trophy },
  { href: "/live", label: "Live", icon: Activity },
  { href: "/predictions", label: "Predictions", icon: LineChart },
  { href: "/worldcup", label: "World Cup", icon: Globe },
  { href: "/models", label: "Models", icon: Brain },
  { href: "/betting", label: "Betting", icon: DollarSign },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed top-4 left-4 z-50 p-2 rounded-lg bg-zinc-900 text-white md:hidden"
        aria-label="Open menu"
      >
        <Menu size={20} />
      </button>

      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        className={`
          fixed md:sticky top-0 left-0 z-40 h-screen
          bg-zinc-900 text-white w-64 flex-shrink-0
          transition-transform duration-200
          ${open ? "translate-x-0" : "-translate-x-full"}
          md:translate-x-0
        `}
      >
        <div className="flex items-center justify-between p-6 border-b border-zinc-700">
          <div>
            <h1 className="text-lg font-bold">Betting Bot</h1>
            <p className="text-xs text-zinc-400">Football Analytics</p>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="p-1 rounded hover:bg-zinc-700 md:hidden"
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium
                  transition-colors
                  ${
                    isActive
                      ? "bg-emerald-600 text-white"
                      : "text-zinc-300 hover:bg-zinc-800 hover:text-white"
                  }
                `}
              >
                <item.icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-6 border-t border-zinc-700">
          <p className="text-xs text-zinc-500">v0.1.0</p>
        </div>
      </aside>
    </>
  );
}
