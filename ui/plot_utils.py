"""
工程比例简图生成器
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io

def draw_schematic(D_mm: float, t_mm: float, L_m: float):
    """绘制截面与立面工程比例简图"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3))
    
    # 1. 截面比例图
    R = D_mm / 2
    r = R - t_mm
    
    c_out = plt.Circle((0, 0), R, color='black', fill=False, linewidth=2)
    c_in = plt.Circle((0, 0), r, color='steelblue', fill=False, linewidth=1, linestyle='--')
    ax1.add_patch(c_out)
    ax1.add_patch(c_in)
    ax1.set_xlim(-R*1.3, R*1.3)
    ax1.set_ylim(-R*1.3, R*1.3)
    ax1.set_aspect('equal')
    ax1.axis('off')
    ax1.set_title(f"截面比例 (D={int(D_mm)}, t={t_mm})", fontsize=10)
    
    # 2. 立面简图
    L_mm = L_m * 1000
    rect = patches.Rectangle((0, -R), L_mm, D_mm, linewidth=2, edgecolor='black', facecolor='lightgray')
    ax2.add_patch(rect)
    
    # 简易支座
    support_w = L_mm * 0.05
    ax2.plot([0, -support_w/2, support_w/2, 0], [-R, -R-D_mm, -R-D_mm, -R], color='black', linewidth=2)
    ax2.plot([L_mm, L_mm-support_w/2, L_mm+support_w/2, L_mm], [-R, -R-D_mm, -R-D_mm, -R], color='black', linewidth=2)
    
    ax2.set_xlim(-L_mm*0.1, L_mm*1.1)
    ax2.set_ylim(-R*2 - D_mm, R*2)
    ax2.set_aspect('equal')
    ax2.axis('off')
    ax2.set_title(f"单跨立面示意 (L={L_m}m)", fontsize=10)
    
    fig.tight_layout()
    return fig
