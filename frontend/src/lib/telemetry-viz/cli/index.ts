#!/usr/bin/env node
/**
 * Telemetry Visualization Library CLI
 *
 * Command-line interface for managing telemetry visualizations,
 * generating chart configurations, and exporting visualizations.
 */

import { program } from 'commander';
import chalk from 'chalk';
import inquirer from 'inquirer';
import fs from 'fs/promises';
import path from 'path';
import { TelemetryProcessor } from '../processors/TelemetryProcessor';
import { ExportUtils } from '../utils/ExportUtils';
import type {
  ChartConfiguration,
  TelemetryDataPoint,
  ExportOptions,
  ChartType
} from '../types';

const LIBRARY_VERSION = '1.0.0';

interface CLIConfig {
  dataSource?: string;
  outputDir?: string;
  defaultTheme?: string;
  defaultFormat?: string;
}

class TelemetryVizCLI {
  private config: CLIConfig = {};
  private processor: TelemetryProcessor;

  constructor() {
    this.processor = new TelemetryProcessor({
      enableCaching: true,
      enableValidation: true
    });
  }

  async loadConfig(): Promise<void> {
    try {
      const configPath = path.join(process.cwd(), 'telemetry-viz.config.json');
      const configData = await fs.readFile(configPath, 'utf-8');
      this.config = JSON.parse(configData);
    } catch (error) {
      // Config file doesn't exist or is invalid, use defaults
      this.config = {
        outputDir: './output',
        defaultTheme: 'light',
        defaultFormat: 'png'
      };
    }
  }

  async saveConfig(): Promise<void> {
    const configPath = path.join(process.cwd(), 'telemetry-viz.config.json');
    await fs.writeFile(configPath, JSON.stringify(this.config, null, 2));
    console.log(chalk.green('✓ Configuration saved'));
  }

  async loadData(filePath: string): Promise<TelemetryDataPoint[]> {
    try {
      const data = await fs.readFile(filePath, 'utf-8');
      const parsed = JSON.parse(data);

      if (!Array.isArray(parsed)) {
        throw new Error('Data file must contain an array of telemetry data points');
      }

      return parsed;
    } catch (error) {
      throw new Error(`Failed to load data from ${filePath}: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async generateChart(options: {
    data: string;
    type: ChartType;
    output?: string;
    config?: string;
    theme?: string;
    title?: string;
    interactive?: boolean;
  }): Promise<void> {
    console.log(chalk.blue('📊 Generating chart...'));

    // Load data
    const telemetryData = await this.loadData(options.data);
    console.log(chalk.gray(`Loaded ${telemetryData.length} data points`));

    // Load or create chart configuration
    let chartConfig: ChartConfiguration;

    if (options.config) {
      const configData = await fs.readFile(options.config, 'utf-8');
      chartConfig = JSON.parse(configData);
    } else {
      chartConfig = {
        type: options.type,
        title: options.title,
        responsive: true,
        animation: true,
        theme: {
          name: options.theme || this.config.defaultTheme || 'light'
        },
        axes: {
          x: {
            type: 'time',
            label: 'Time'
          },
          y: {
            type: 'numeric',
            label: 'Value'
          }
        },
        legend: {
          show: true,
          position: 'top'
        },
        tooltip: {
          show: true
        }
      };
    }

    // Process data
    const processedData = this.processor.processData(telemetryData, {
      sorting: { field: 'timestamp', direction: 'asc' }
    });

    // Generate output
    const outputPath = options.output || path.join(
      this.config.outputDir || './output',
      `chart-${Date.now()}.html`
    );

    await this.ensureDirectoryExists(path.dirname(outputPath));

    if (options.interactive) {
      await this.generateInteractiveChart(processedData, chartConfig, outputPath);
    } else {
      await this.generateStaticChart(processedData, chartConfig, outputPath);
    }

    console.log(chalk.green(`✓ Chart generated: ${outputPath}`));
  }

  async generateInteractiveChart(
    data: TelemetryDataPoint[],
    config: ChartConfiguration,
    outputPath: string
  ): Promise<void> {
    const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${config.title || 'Telemetry Chart'}</title>
    <script src="https://cdn.jsdelivr.net/npm/@visactor/vchart@1.11.0/build/index.min.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: ${config.theme?.colors?.background || '#ffffff'};
        }
        .chart-container {
            width: 100%;
            height: 600px;
            border: 1px solid #e1e5e9;
            border-radius: 8px;
            background: white;
        }
        .chart-header {
            padding: 16px;
            border-bottom: 1px solid #e1e5e9;
            background: #f8f9fa;
        }
        .chart-title {
            font-size: 18px;
            font-weight: 600;
            margin: 0;
            color: #2c3e50;
        }
        .chart-stats {
            font-size: 12px;
            color: #6c757d;
            margin-top: 4px;
        }
    </style>
</head>
<body>
    <div class="chart-header">
        <h1 class="chart-title">${config.title || 'Telemetry Visualization'}</h1>
        <div class="chart-stats">
            ${data.length} data points |
            ${new Set(data.map(d => d.field)).size} fields |
            ${new Set(data.map(d => d.deviceId)).size} devices
        </div>
    </div>
    <div id="chart" class="chart-container"></div>

    <script>
        const data = ${JSON.stringify(data)};
        const config = ${JSON.stringify(config)};

        // Transform data for VChart
        const chartData = [];
        const fieldGroups = {};

        data.forEach(point => {
            if (!fieldGroups[point.field]) {
                fieldGroups[point.field] = [];
            }
            fieldGroups[point.field].push({
                x: new Date(point.timestamp).getTime(),
                y: point.value,
                field: point.field,
                deviceId: point.deviceId
            });
        });

        Object.entries(fieldGroups).forEach(([field, values]) => {
            chartData.push({
                name: field,
                values: values.sort((a, b) => a.x - b.x)
            });
        });

        // Create chart specification
        const spec = {
            type: config.type,
            data: chartData,
            xField: 'x',
            yField: 'y',
            seriesField: 'field',
            axes: [
                {
                    orient: 'bottom',
                    type: 'time',
                    label: {
                        formatMethod: (value) => new Date(value).toLocaleTimeString()
                    }
                },
                {
                    orient: 'left',
                    type: 'linear'
                }
            ],
            legends: [{
                visible: true,
                position: 'top'
            }],
            tooltip: {
                visible: true,
                mark: {
                    content: [
                        {
                            key: 'Time',
                            value: (datum) => new Date(datum.x).toLocaleString()
                        },
                        {
                            key: 'Value',
                            value: (datum) => datum.y
                        },
                        {
                            key: 'Device',
                            value: 'deviceId'
                        }
                    ]
                }
            }
        };

        // Render chart
        const chart = new VChart(spec, { dom: 'chart' });
        chart.renderAsync();

        // Handle window resize
        window.addEventListener('resize', () => {
            chart.resize();
        });
    </script>
</body>
</html>`;

    await fs.writeFile(outputPath, html);
  }

  async generateStaticChart(
    data: TelemetryDataPoint[],
    config: ChartConfiguration,
    outputPath: string
  ): Promise<void> {
    // For static charts, we would use a headless browser or server-side rendering
    // This is a simplified implementation that generates an HTML file
    console.log(chalk.yellow('Note: Static chart generation requires additional dependencies'));
    await this.generateInteractiveChart(data, config, outputPath);
  }

  async createTemplate(type: ChartType, outputPath: string): Promise<void> {
    const templates = {
      line: {
        type: 'line',
        title: 'Line Chart Template',
        responsive: true,
        animation: true,
        axes: {
          x: { type: 'time', label: 'Time' },
          y: { type: 'numeric', label: 'Value' }
        },
        legend: { show: true, position: 'top' },
        tooltip: { show: true }
      },
      area: {
        type: 'area',
        title: 'Area Chart Template',
        responsive: true,
        animation: true,
        axes: {
          x: { type: 'time', label: 'Time' },
          y: { type: 'numeric', label: 'Value' }
        }
      },
      bar: {
        type: 'bar',
        title: 'Bar Chart Template',
        responsive: true,
        axes: {
          x: { type: 'category', label: 'Category' },
          y: { type: 'numeric', label: 'Value' }
        }
      },
      scatter: {
        type: 'scatter',
        title: 'Scatter Plot Template',
        responsive: true,
        axes: {
          x: { type: 'numeric', label: 'X Value' },
          y: { type: 'numeric', label: 'Y Value' }
        }
      },
      heatmap: {
        type: 'heatmap',
        title: 'Heatmap Template',
        responsive: true
      },
      gauge: {
        type: 'gauge',
        title: 'Gauge Chart Template',
        responsive: true
      }
    };

    const template = templates[type];
    if (!template) {
      throw new Error(`Unknown chart type: ${type}`);
    }

    await this.ensureDirectoryExists(path.dirname(outputPath));
    await fs.writeFile(outputPath, JSON.stringify(template, null, 2));
    console.log(chalk.green(`✓ Template created: ${outputPath}`));
  }

  async analyzeData(filePath: string): Promise<void> {
    console.log(chalk.blue('🔍 Analyzing telemetry data...'));

    const data = await this.loadData(filePath);

    // Basic statistics
    const fields = new Set(data.map(d => d.field));
    const devices = new Set(data.map(d => d.deviceId));
    const timeRange = data.length > 0 ? {
      start: new Date(Math.min(...data.map(d => new Date(d.timestamp).getTime()))),
      end: new Date(Math.max(...data.map(d => new Date(d.timestamp).getTime())))
    } : null;

    // Field statistics
    const fieldStats: Record<string, any> = {};
    fields.forEach(field => {
      const fieldData = data.filter(d => d.field === field);
      const values = fieldData.map(d => d.value);

      fieldStats[field] = {
        count: values.length,
        min: Math.min(...values),
        max: Math.max(...values),
        avg: values.reduce((sum, v) => sum + v, 0) / values.length,
        devices: new Set(fieldData.map(d => d.deviceId)).size
      };
    });

    console.log(chalk.green('\n📈 Data Analysis Results:'));
    console.log(`Total data points: ${chalk.bold(data.length.toLocaleString())}`);
    console.log(`Fields: ${chalk.bold(fields.size)}`);
    console.log(`Devices: ${chalk.bold(devices.size)}`);

    if (timeRange) {
      console.log(`Time range: ${chalk.bold(timeRange.start.toLocaleString())} to ${chalk.bold(timeRange.end.toLocaleString())}`);
      const duration = timeRange.end.getTime() - timeRange.start.getTime();
      console.log(`Duration: ${chalk.bold(this.formatDuration(duration))}`);
    }

    console.log('\n📊 Field Statistics:');
    Object.entries(fieldStats).forEach(([field, stats]) => {
      console.log(`  ${chalk.cyan(field)}:`);
      console.log(`    Count: ${stats.count.toLocaleString()}`);
      console.log(`    Range: ${stats.min} - ${stats.max}`);
      console.log(`    Average: ${stats.avg.toFixed(2)}`);
      console.log(`    Devices: ${stats.devices}`);
    });
  }

  private formatDuration(ms: number): string {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days} days`;
    if (hours > 0) return `${hours} hours`;
    if (minutes > 0) return `${minutes} minutes`;
    return `${seconds} seconds`;
  }

  private async ensureDirectoryExists(dirPath: string): Promise<void> {
    try {
      await fs.access(dirPath);
    } catch {
      await fs.mkdir(dirPath, { recursive: true });
    }
  }
}

// Initialize CLI
const cli = new TelemetryVizCLI();

program
  .name('telemetry-viz')
  .description('Telemetry Visualization Library CLI')
  .version(LIBRARY_VERSION);

// Init command
program
  .command('init')
  .description('Initialize configuration file')
  .option('-d, --data-source <source>', 'Default data source')
  .option('-o, --output-dir <dir>', 'Default output directory', './output')
  .option('-t, --theme <theme>', 'Default theme', 'light')
  .action(async (options) => {
    await cli.loadConfig();

    const answers = await inquirer.prompt([
      {
        type: 'input',
        name: 'dataSource',
        message: 'Default data source:',
        default: options.dataSource || cli['config'].dataSource
      },
      {
        type: 'input',
        name: 'outputDir',
        message: 'Output directory:',
        default: options.outputDir || cli['config'].outputDir || './output'
      },
      {
        type: 'list',
        name: 'defaultTheme',
        message: 'Default theme:',
        choices: ['light', 'dark', 'minimal'],
        default: options.theme || cli['config'].defaultTheme || 'light'
      }
    ]);

    cli['config'] = { ...cli['config'], ...answers };
    await cli.saveConfig();
  });

// Generate command
program
  .command('generate')
  .description('Generate a chart from telemetry data')
  .requiredOption('-d, --data <file>', 'Input data file (JSON)')
  .requiredOption('-t, --type <type>', 'Chart type (line, area, bar, scatter, heatmap, gauge)')
  .option('-o, --output <file>', 'Output file path')
  .option('-c, --config <file>', 'Chart configuration file')
  .option('--theme <theme>', 'Chart theme')
  .option('--title <title>', 'Chart title')
  .option('--interactive', 'Generate interactive chart', false)
  .action(async (options) => {
    await cli.loadConfig();
    await cli.generateChart(options);
  });

// Template command
program
  .command('template')
  .description('Create a chart configuration template')
  .requiredOption('-t, --type <type>', 'Chart type (line, area, bar, scatter, heatmap, gauge)')
  .requiredOption('-o, --output <file>', 'Output template file')
  .action(async (options) => {
    await cli.createTemplate(options.type as ChartType, options.output);
  });

// Analyze command
program
  .command('analyze')
  .description('Analyze telemetry data file')
  .requiredOption('-d, --data <file>', 'Input data file (JSON)')
  .action(async (options) => {
    await cli.analyzeData(options.data);
  });

// Export the CLI for programmatic use
export { cli, TelemetryVizCLI };

// Run CLI if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  program.parse();
}