import {
  BookOpenIcon,
  FileTextIcon,
  HomeIcon,
  MessageCircleIcon,
  SettingsIcon,
  ShieldCheckIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useAuthStore } from "@/store/authStore";

const mainNav = [
  { to: "/home", label: "홈", icon: HomeIcon },
  { to: "/documents", label: "내 문서", icon: FileTextIcon },
  { to: "/health-guide", label: "건강 가이드", icon: BookOpenIcon },
  { to: "/chat", label: "챗봇", icon: MessageCircleIcon },
  { to: "/settings", label: "설정", icon: SettingsIcon },
];

const adminNav = [{ to: "/admin", label: "관리자", icon: ShieldCheckIcon }];

export default function AppSidebar() {
  const role = useAuthStore((s) => s.user?.role);

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1">
          <div className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground text-sm font-semibold">
            M
          </div>
          <span className="text-sm font-semibold group-data-[collapsible=icon]:hidden">
            Medi-Mate
          </span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>메뉴</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainNav.map((item) => (
                <SidebarMenuItem key={item.to}>
                  <NavLink to={item.to}>
                    {({ isActive }) => (
                      <SidebarMenuButton asChild isActive={isActive} tooltip={item.label}>
                        <span className="flex items-center gap-2">
                          <item.icon />
                          <span>{item.label}</span>
                        </span>
                      </SidebarMenuButton>
                    )}
                  </NavLink>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      {role === "admin" && (
        <SidebarFooter>
          <SidebarMenu>
            {adminNav.map((item) => (
              <SidebarMenuItem key={item.to}>
                <NavLink to={item.to}>
                  {({ isActive }) => (
                    <SidebarMenuButton asChild isActive={isActive} tooltip={item.label}>
                      <span className="flex items-center gap-2">
                        <item.icon />
                        <span>{item.label}</span>
                      </span>
                    </SidebarMenuButton>
                  )}
                </NavLink>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarFooter>
      )}
    </Sidebar>
  );
}
