import sys
import inspect

data = {}
trace_obj = None

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <style>
        .viewport-container {
            width: 100vw;
            height: 100vh;
            overflow: auto;
            position: fixed;
            top: 0;
            left: 0;
            background: #f0f0f0;
        }

        .transform-container {
            position: relative;
            transition: transform 0.1s ease;
        }

        .func-rect {
            position: absolute;
            background-color: var(--main-color);
            border: 1px solid #333;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: 
                background-color 1s,
                width 1s,
                height 1s,
                left 1s,
                top 1s;
            height: 40px;
            box-sizing: border-box;
        }

        .func-rect:hover {
            background-color: var(--hover-color);
        }

        .secondary-popup {
            position: absolute;
            background: white;
            border: 1px solid #333;
            padding: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
            transition: 
                background-color 1s,
                width 1s,
                height 1s,
                left 1s,
                top 1s;
            color: black;
        }
    </style>
</head>
<body>
    <div class="viewport-container">
        <div class="transform-container"></div>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const data = %s
            const rootNode = data.func_data[data.root];

            const rects = [];
            const viewport = document.querySelector('.viewport-container');
            const transformContainer = document.querySelector('.transform-container');

            let BASE_WIDTH = document.documentElement.clientWidth / rootNode.total_lines; // width unit
            let BASE_HEIGHT = 20; // height unit
            let scaleFactor = 1;
            let isDragging = false;
            let startX, startY, scrollLeft, scrollTop;
            let activePopup = null;
            let activeRect = null;

            // generate random function
            const getRandomColor = () => '#' + 
                Math.floor(Math.random()*16777215).toString(16).padStart(6, '0');

            // darken a given color
            const darkenColor = (hex, percent) => {
                const num = parseInt(hex.slice(1), 16);
                const [r, g, b] = [
                    Math.max(0, (num >> 16) * (1 - percent)),
                    Math.max(0, ((num >> 8) & 0xff) * (1 - percent)),
                    Math.max(0, (num & 0xff) * (1 - percent))
                ];
                return '#' + [r, g, b].map(v => 
                    Math.round(v).toString(16).padStart(2, '0')).join('');
            };

            // remove popup window
            function removePopup() {
                if (activePopup) {
                    activePopup.remove();
                    activePopup = null;
                    activeRect = null;
                }
            }

            // create popup window (to container)
            function createPopup(popup, rect, transformContainer) {
                removePopup();
                transformContainer.appendChild(popup);
                activePopup = popup;
                activeRect = rect;
                updatePopup();
            }

            // init rect given the node
            function createFunctionRect(nodeInfo, level, startPos, parentStart = 0) {
                const rect = document.createElement('div');
                rect.className = 'func-rect';
                const baseColor = getRandomColor();
                const hoverColor = darkenColor(baseColor, 0.2);
                rect.style.setProperty('--main-color', baseColor);
                rect.style.setProperty('--hover-color', hoverColor);
                rect.textContent = `${Object.keys(data.func_data).find(k => data.func_data[k] === nodeInfo)}`;

                const rectData = {
                    level,
                    startPos,
                    parentStart,
                    totalLines: nodeInfo.total_lines,
                };
                rects.push({element: rect, data: rectData});

                rect.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (activeRect === rect) return;
                    
                    const popup = document.createElement('div');
                    popup.className = 'secondary-popup';
                    popup.innerHTML = `
                        <h3>Detail</h3>
                        <p>Before: ${nodeInfo.call_v}</p>
                        <p>After: ${nodeInfo.return_v}</p>
                    `;
                    createPopup(popup, rect, transformContainer);
                });
                
                transformContainer.appendChild(rect);
                updateRect(rect, rectData);

                // iter over children
                if (nodeInfo.children_infos) {
                    nodeInfo.children_infos.forEach(([childName, childStart]) => {
                        const childNode = data.func_data[childName];
                        if (childNode) {
                            createFunctionRect(childNode, level + 1, childStart - 1, parentStart + startPos);
                        }
                    });
                }
            }

            // update all rects
            function updateAllRects() {
                rects.forEach(({element, data}) => {
                    updateRect(element, data);
                });
                updatePopup();
                updateContainerSize();
            }

            // update popup pos
            function updatePopup() {
                if (activePopup && activeRect) {
                    const rectTop = parseFloat(activeRect.style.top);
                    const rectLeft = parseFloat(activeRect.style.left);
                    const rectHeight = parseFloat(activeRect.style.height);
                    activePopup.style.top = `${rectTop + rectHeight}px`;
                    activePopup.style.left = `${rectLeft}px`;
                }
            }

            // update single rect size and pos
            function updateRect(rect, data) {
                const currentWidth = data.totalLines * BASE_WIDTH * scaleFactor;
                const currentHeight = BASE_HEIGHT * scaleFactor;
                const currentLeft = (data.parentStart + data.startPos) * BASE_WIDTH * scaleFactor;
                const currentTop = data.level * BASE_HEIGHT * scaleFactor;

                rect.style.width = `${currentWidth}px`;
                rect.style.height = `${currentHeight}px`;
                rect.style.left = `${currentLeft}px`;
                rect.style.top = `${currentTop}px`;
            }

            // update container
            function updateContainerSize() {
                let maxRight = 0;
                let maxBottom = 0;
                
                rects.forEach(({data}) => {
                    const right = (data.parentStart + data.startPos + data.totalLines) * BASE_WIDTH * scaleFactor;
                    const bottom = (data.level + 1) * 60 * scaleFactor;
                    if (right > maxRight) maxRight = right;
                    if (bottom > maxBottom) maxBottom = bottom;
                });

                transformContainer.style.width = `${maxRight}px`;
                transformContainer.style.height = `${maxBottom}px`;
            }

            // wheel zoom
            viewport.addEventListener('wheel', (e) => {
                e.preventDefault();
                const delta = e.deltaY > 0 ? 0.9 : 1.1;
                scaleFactor = Math.min(10, Math.max(1.0, scaleFactor * delta));
                updateAllRects();
            }, { passive: false });

            // mouse down
            viewport.addEventListener('mousedown', (e) => {
                isDragging = true;
                startX = e.pageX - viewport.offsetLeft;
                startY = e.pageY - viewport.offsetTop;
                scrollLeft = viewport.scrollLeft;
                scrollTop = viewport.scrollTop;
            });

            // update scroll pos
            document.addEventListener('mousemove', (e) => {
                if (!isDragging) return;
                e.preventDefault();
                const x = e.pageX - viewport.offsetLeft;
                const y = e.pageY - viewport.offsetTop;
                viewport.scrollLeft = scrollLeft + (startX - x);
                viewport.scrollTop = scrollTop + (startY - y);
            });

            // mose up
            document.addEventListener('mouseup', () => {
                isDragging = false;
            });
            
            document.addEventListener('click', (e) => {
                if (activePopup && !activePopup.contains(e.target)) {
                    removePopup();
                }
            });

            // listen to viewport resizing
            window.addEventListener('resize', debounce(() => {
                initBaseWidth();
            }, 100));

            // dirty call
            function debounce(func, wait) {
                let timeout;
                return function(...args) {
                    clearTimeout(timeout);
                    timeout = setTimeout(() => func.apply(this, args), wait);
                };
            }

            // refresh base width
            function initBaseWidth() {
                BASE_WIDTH = document.documentElement.clientWidth / rootNode.total_lines;
                updateAllRects();
            }

            // initialize rects
            if (rootNode) {
                createFunctionRect(rootNode, 0, 0);
                updateContainerSize();
            }
        });
        </script>
</body>
</html>

'''

def update_data(event, frame):
    fn = frame.f_code.co_name
    if fn == 'end_trace' or fn == 'start_trace' or fn == 'update_data':
        return
    global data
    if fn not in data:
        data[fn] = {}
    fn_fln = frame.f_code.co_firstlineno
    fn_ln = frame.f_lineno
    data[fn][event+'_v'] = trace_obj.v
    data[fn][event+'_ln'] = fn_ln # exec line
    data[fn]['fn_fln'] = fn_fln # func line
    fb = frame.f_back
    if fb:
        fb_fn = fb.f_code.co_name
        if fb_fn not in data:
            data[fb_fn] = {}
        if 'children' not in data[fb_fn]:
            data[fb_fn]['children'] = []
        if 'children_ln' not in data[fb_fn]:
            data[fb_fn]['children_ln'] = []
        if fn not in data[fb_fn]['children']:
            fb_ln = fb.f_lineno
            data[fb_fn]['children'].append(fn)
            data[fb_fn]['children_ln'].append(fb_ln)

def trace_calls(frame, event, arg):
    global data
    if event == 'call':
        update_data('call', frame)
    elif event == 'return':
        update_data('return', frame)
    return trace_calls

def start_trace(t):
    global data
    global trace_obj
    data = {}
    trace_obj = t
    f = inspect.currentframe()
    sys.settrace(trace_calls)
    update_data('call', f.f_back)

def end_trace():
    global data
    global trace_obj
    sys.settrace(None)
    f = inspect.currentframe()
    update_data('return', f.f_back)
    process_data()
    for k,v in data.items():
        print(k, v)
    data = {}
    trace_obj = None


def process_data():
    global data
    invalid_ks = []
    cs = set()
    root = None
    for k,v in data.items():
        if 'call_v' not in v:
            invalid_ks.append(k)
        else:
            for c in v.get('children', ()):
                cs.add(c)
    for k in invalid_ks:
        del data[k]
    for k in data.keys():
        if k not in cs:
            root = k
            break

    def calc_func_len(node):
        if node not in data:
            return 0
        d = data[node]
        children_infos = []
        for c, cl in zip(d.get('children', ()), d.get('children_ln', ())):
            children_infos.append([c, cl])
        if children_infos:
            children_infos.sort(key=lambda x: x[1])
            data[node]['children_infos'] = children_infos
        if 'children' in d:
            del data[node]['children']
        if 'children_ln' in d:
            del data[node]['children_ln']

        total_lines = d['return_ln'] - d['call_ln']
        new_lines = 0
        for child_info in children_infos:
            node_lines = calc_func_len(child_info[0])
            child_info[1] += new_lines
            new_lines += node_lines - 1
            total_lines += node_lines - 1
        data[node]['total_lines'] = total_lines
        for child_info in children_infos:
            child_info[1] -= d['call_ln']
        del data[node]['call_ln']
        del data[node]['return_ln']
        return total_lines
    calc_func_len(root)

    func_data = {}
    func_data.update(data)
    final_data = {
        'root': root,
        'func_data': func_data,
    }
    html = HTML_TEMPLATE % final_data
    filename = 'tracer.html'
    with open(filename, 'w') as f:
        f.write(html)

class T(object):
    def __init__(self):
        self.v = 0

    def t1(self):
        self.v += 1
        self.t2()
        self.v += 1

    def t2(self):
        self.v -= 4

def f():
    t = T()
    start_trace(t)
    t.v += 10
    g(t)
    h(t)
    t.v -= 5
    end_trace()

def g(t):
    t.v += 2
    g1(t)
    g2()
    t.v += 3

def g1(t):
    t.v += 1

def g2():
    pass

def h(t):
    t.v += 4
    t.t1()

def p():
    print('Over...')

f()
p()
