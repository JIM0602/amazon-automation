"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

interface NavItem {
  href: string;
  label: string;
  icon: string;
  /** Only shown to users with role=boss */
  bossOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "仪表盘", icon: "📊" },
  { href: "/agents", label: "Agent 管理", icon: "🤖" },
  { href: "/system", label: "系统管理", icon: "⚙️", bossOnly: true },
];

/**
 * Fixed left sidebar navigation.
 * Highlights the active route. Boss-only items are hidden for operators.
 */
export default function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();

  return (
    <aside className="fixed left-0 top-14 bottom-0 w-64 bg-gray-800 text-white flex flex-col border-r border-gray-700">
      <nav className="flex-1 py-4 overflow-y-auto">
        <ul className="space-y-1 px-3">
          {NAV_ITEMS.map((item) => {
            // Hide boss-only items for non-boss users
            if (item.bossOnly && user?.role !== "boss") return null;

            const isActive =
              pathname === item.href || pathname.startsWith(item.href + "/");

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`
                    flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all
                    ${
                      isActive
                        ? "bg-blue-600 text-white"
                        : "text-gray-300 hover:bg-gray-700 hover:text-white"
                    }
                  `}
                >
                  <span className="text-base">{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-700">
        <p className="text-xs text-gray-500">v0.1.0</p>
      </div>
    </aside>
  );
}
