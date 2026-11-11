"""Export a scientific diagnostic figure from synchronized experiment data."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle


def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('folder',type=Path);cli.add_argument('output',type=Path);args=cli.parse_args()
    data=json.loads((args.folder/'synchronized.json').read_text())
    analysis=json.loads((args.folder/'analysis.json').read_text())
    solids=json.loads((args.folder/'generated/solids.json').read_text())
    fig,(ax,trace)=plt.subplots(1,2,figsize=(11,4.3),layout='constrained')
    for solid in solids:
        b=solid['bounds'];ax.add_patch(Rectangle((b['x_min'],b['y_min']),b['x_max']-b['x_min'],b['y_max']-b['y_min'],facecolor='#cbd5e1',edgecolor='#64748b'))
    for key,label,color in [('physical','Gazebo fiziksel merkez','#0369a1'),('map_pose','TF map tahmini','#c2410c')]:
        ax.plot([r[key][0] for r in data],[r[key][1] for r in data],label=label,color=color,lw=1.5)
        end=data[-1][key]
        ax.add_patch(Circle(end[:2],.31,fill=False,color=color,ls='--',lw=1.2))
    ax.plot([2.25],[5.75],marker='x',ms=8,color='#15803d',label='pick_A2')
    ax.add_patch(Circle((2.25,5.75),.35,fill=False,color='#15803d',ls=':'))
    ax.set(xlim=(1.4,6),ylim=(4.8,8.3),xlabel='Map X (m)',ylabel='Map Y (m)',title='Aynı damgalı konumlar ve 0,31 m zarf')
    ax.set_aspect('equal');ax.legend(loc='lower right',fontsize=8);ax.grid(alpha=.15)
    t0=data[0]['stamp_ns'];ts=[(r['stamp_ns']-t0)/1e9 for r in data]
    trace.plot(ts,[r['error_m'] for r in data],label='Map–fiziksel fark (m)',color='#7c3aed')
    trace.plot(ts,[r['rack_A2_physical_distance_m'] for r in data],label='Fiziksel merkez–raf (m)',color='#0369a1')
    trace.plot(ts,[r['rack_A2_map_distance_m'] for r in data],label='Map merkezi–raf (m)',color='#c2410c')
    trace.axhline(.31,color='#b91c1c',ls='--',label='Padding ile güvenli yarıçap')
    trace.set(xlabel='Başlangıçtan simülasyon zamanı (s)',ylabel='Mesafe (m)',ylim=(0,1.2),title=f"Nav2={analysis['nav2_terminal']}; fiziksel hata={analysis['physical_error_m']:.3f} m")
    trace.legend(fontsize=8);trace.grid(alpha=.15)
    fig.suptitle(args.folder.parent.name+'/'+args.folder.name,fontsize=12)
    fig.savefig(args.output,dpi=160);plt.close(fig)

if __name__=='__main__':main()
