import AppKit
import SwiftUI

private struct PanelSize: PreferenceKey {
    static let defaultValue = CGSize.zero
    static func reduce(value: inout CGSize, nextValue: () -> CGSize) { value = nextValue() }
}

private final class PanelDocument: NSView {
    override var isFlipped: Bool { true }
}

final class MenuPanel: NSObject {
    let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    let popover = NSPopover()
    private let scroll = NSScrollView()
    private let document = PanelDocument()
    private var hostedView: NSView?

    func configure<Content: View>(_ content: Content) {
        let measured = content.fixedSize().background(GeometryReader { geometry in
            Color.clear.preference(key: PanelSize.self, value: geometry.size)
        }).onPreferenceChange(PanelSize.self) { [weak self] _ in
            DispatchQueue.main.async {
                guard let self, self.popover.isShown else { return }
                self.fitContent()
            }
        }
        let host = NSHostingView(rootView: measured)
        hostedView = host
        document.addSubview(host)
        scroll.documentView = document
        scroll.drawsBackground = false
        scroll.scrollerStyle = .overlay
        let controller = NSViewController()
        controller.view = scroll
        popover.contentViewController = controller
        popover.behavior = .transient
        item.button?.target = self
        item.button?.action = #selector(toggle)
    }

    private func fitContent() {
        guard let host = hostedView else { return }
        let ideal = host.fittingSize
        guard ideal.width > 0, ideal.height > 0 else { return }
        let size = NSSize(width: ceil(ideal.width), height: ceil(ideal.height))
        let available = item.button?.window?.screen?.visibleFrame.height ?? size.height + 32
        let viewport = NSSize(width: size.width, height: min(size.height, max(1, available - 32)))
        host.frame = NSRect(origin: .zero, size: size)
        document.setFrameSize(size)
        scroll.hasVerticalScroller = viewport.height < size.height
        if popover.contentSize != viewport { popover.contentSize = viewport }
    }

    // Exercise the window geometry after AppKit has finished positioning the popover.
    func verifyVisibleContent() {
        guard let window = scroll.window, let screen = item.button?.window?.screen else {
            fputs("Missing viewport, shown=\(popover.isShown) view=\(String(describing: scroll.window)) anchor=\(String(describing: item.button?.window?.frame)) screen=\(String(describing: item.button?.window?.screen))\n", stderr)
            exit(1)
        }
        let viewport = window.convertToScreen(scroll.convert(scroll.bounds, to: nil))
        fputs("Panel viewport: "+NSStringFromRect(viewport)+" screen: "+NSStringFromRect(screen.visibleFrame)+"\n", stderr)
        precondition(screen.visibleFrame.insetBy(dx: -1, dy: -1).contains(viewport),
                     "Popover viewport extends beyond the usable screen: "+NSStringFromRect(viewport))
        precondition(document.frame.height <= scroll.contentSize.height + 1 || scroll.hasVerticalScroller)
        print("Verified visible panel:", NSStringFromRect(viewport))
    }

    @objc func toggle() {
        if popover.isShown { popover.performClose(nil) } else { show() }
    }
    @objc func show() {
        guard let button = item.button else { return }
        fitContent()
        scroll.contentView.scroll(to: .zero)
        scroll.reflectScrolledClipView(scroll.contentView)
        NSApp.activate(ignoringOtherApps: true)
        popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
    }
}

struct PanelGlyph: View {
    let symbol: String
    let color: Color

    var body: some View {
        Image(systemName: symbol)
            .font(.system(size: 15, weight: .semibold))
            .foregroundStyle(color)
            .frame(width: 22, height: 22)
            .accessibilityHidden(true)
    }
}

struct PanelHeading: View {
    let name: String
    let symbol: String
    let color: Color
    var body: some View {
        HStack(spacing: 12) {
            PanelGlyph(symbol: symbol, color: color)
            Text(name).font(.system(size: 17, weight: .semibold))
            Spacer()
            Text("v" + (Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? ""))
                .font(.caption).foregroundStyle(.secondary)
        }
    }
}

func ink(_ text: String, _ font: NSFont) -> NSAttributedString {
    NSAttributedString(string: text, attributes: [.font: font, .foregroundColor: NSColor.black])
}

func quotaFont(for number: String) -> NSFont {
    .monospacedDigitSystemFont(ofSize: number.count > 2 ? 9 : 10.5, weight: .bold)
}

func ringImage(number: String, fraction: Double?, marker: String) -> NSImage {
    let image = NSImage(size: NSSize(width: 28, height: 24), flipped: false) { _ in
        let gap: CGFloat = marker == "H" ? 54 : marker == "W" ? 68 : 64
        let start = 270 - gap / 2
        for (opacity, progress) in [(0.28, 1.0), (1.0, fraction ?? 0)] where progress > 0 {
            NSColor.black.withAlphaComponent(opacity).setStroke()
            let arc = NSBezierPath()
            arc.lineWidth = 2.4
            arc.lineCapStyle = .round
            arc.appendArc(withCenter: NSPoint(x: 14, y: 12), radius: 10.7,
                          startAngle: start, endAngle: start - (360-gap)*progress, clockwise: true)
            arc.stroke()
        }
        let font = quotaFont(for: number)
        let digits = ink(number, font)
        digits.draw(at: NSPoint(x: 14 - digits.size().width/2, y: 8.5))
        if marker == "sun" {
            NSImage(systemSymbolName: "sun.max.fill", accessibilityDescription: nil)?
                .withSymbolConfiguration(.init(paletteColors: [.black]))?.draw(in: NSRect(x: 10, y: 0, width: 8, height: 8))
        } else {
            let label = ink(marker, font)
            label.draw(at: NSPoint(x: 14-label.size().width/2, y: -1))
        }
        return true
    }
    image.isTemplate = true
    return image
}
