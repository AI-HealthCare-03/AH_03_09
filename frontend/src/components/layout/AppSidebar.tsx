import {
  BookOpenIcon,
  FileTextIcon,
  HeartPulseIcon,
  HomeIcon,
  LogOutIcon,
  MessageCircleIcon,
  PanelLeftIcon,
  PillIcon,
  ScanSearchIcon,
} from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { logout } from "@/api/auth";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useAuthStore } from "@/store/authStore";

const mainNav = [
  { to: "/home", label: "홈", icon: HomeIcon },
  { to: "/upload", label: "업로드", icon: ScanSearchIcon },
  { to: "/documents", label: "내 문서", icon: FileTextIcon },
  { to: "/health-guide", label: "건강 가이드", icon: BookOpenIcon },
  { to: "/health-profile", label: "내 건강정보", icon: HeartPulseIcon },
  { to: "/pharmacy", label: "약국 재고", icon: PillIcon },
  { to: "/chat", label: "챗봇", icon: MessageCircleIcon },
];

export default function AppSidebar() {
  const navigate = useNavigate();
  const clear = useAuthStore((s) => s.clear);

  const handleLogout = async () => {
    await logout();
    clear();
    navigate("/");
  };

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="p-2">
        <div className="flex items-center justify-between gap-2 group-data-[collapsible=icon]:flex-col group-data-[collapsible=icon]:gap-1">
          <LogoButton />
          <SidebarTrigger className="size-7 group-data-[collapsible=icon]:hidden" />
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup className="px-2">
          <SidebarGroupContent>
            <SidebarMenu className="gap-0.5">
              {mainNav.map((item) => (
                <SidebarMenuItem key={item.to}>
                  <NavLink to={item.to}>
                    {({ isActive }) => (
                      <SidebarMenuButton
                        asChild
                        isActive={isActive}
                        tooltip={item.label}
                        className="h-10 gap-3 rounded-lg px-3 text-sm font-medium [&>svg]:size-5"
                      >
                        <span className="flex items-center gap-3">
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
      <SidebarFooter className="px-2 pb-3">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              tooltip="로그아웃"
              onClick={handleLogout}
              className="h-10 gap-3 rounded-lg px-3 text-sm font-medium text-slate-500 hover:text-destructive [&>svg]:size-5"
            >
              <LogOutIcon />
              <span>로그아웃</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}

function LogoButton() {
  const { state, toggleSidebar } = useSidebar();
  const navigate = useNavigate();
  const collapsed = state === "collapsed";

  const handleClick = () => {
    if (collapsed) {
      toggleSidebar();
    } else {
      navigate("/home");
    }
  };

  const button = (
    <button
      type="button"
      onClick={handleClick}
      aria-label={collapsed ? "사이드바 열기" : "홈으로"}
      className="group/logo flex items-center gap-2 rounded-md px-1.5 py-1 hover:bg-sidebar-accent"
    >
      <span className="relative grid size-7 shrink-0 place-items-center rounded-md bg-primary text-xs font-bold text-primary-foreground">
        <span className={collapsed ? "transition-opacity group-hover/logo:opacity-0" : ""}>M</span>
        {collapsed ? (
          <PanelLeftIcon className="absolute size-4 opacity-0 transition-opacity group-hover/logo:opacity-100" />
        ) : null}
      </span>
      <span className="text-sm font-semibold group-data-[collapsible=icon]:hidden">Medi-Mate</span>
    </button>
  );

  if (!collapsed) return button;

  return (
    <Tooltip>
      <TooltipTrigger asChild>{button}</TooltipTrigger>
      <TooltipContent side="right" align="center">
        사이드바 열기
      </TooltipContent>
    </Tooltip>
  );
}
